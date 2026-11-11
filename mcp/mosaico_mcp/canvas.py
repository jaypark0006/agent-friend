"""480x480 AMOLED baseline JPEG loader, validator, converter, and zero-dep generator."""

from __future__ import annotations

import base64
import io
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.request

from .discovery import _DIRECT_OPENER

MAX_JPEG_BYTES = 256 * 1024

# Standard ITU-T.81 Annex K Huffman tables for zero-dependency 480x480 solid JPEG synthesis
_STD_DC_LUMINANCE_BITS = bytes([0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0])
_STD_DC_LUMINANCE_VALS = bytes([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])

_STD_DC_CHROMINANCE_BITS = bytes([0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
_STD_DC_CHROMINANCE_VALS = bytes([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])

# Minimal valid AC Huffman tables (only symbol 0x00 = EOB needed for uniform 8x8 blocks)
_MIN_AC_BITS = bytes([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
_MIN_AC_VALS = bytes([0x00])


def _build_huff_codes(bits: bytes, vals: bytes) -> dict[int, tuple[int, int]]:
    codes: dict[int, tuple[int, int]] = {}
    code = 0
    idx = 0
    for length in range(1, 17):
        count = bits[length - 1]
        for _ in range(count):
            codes[vals[idx]] = (code, length)
            code += 1
            idx += 1
        code <<= 1
    return codes


_DC_LUM_CODES = _build_huff_codes(_STD_DC_LUMINANCE_BITS, _STD_DC_LUMINANCE_VALS)
_DC_CHR_CODES = _build_huff_codes(_STD_DC_CHROMINANCE_BITS, _STD_DC_CHROMINANCE_VALS)


def parse_hex_rgb(color: str, default: tuple[int, int, int] = (16, 23, 32)) -> tuple[int, int, int]:
    """Parse `#RRGGBB` or `#RGB` into `(r, g, b)`."""
    raw = (color or "").strip().lstrip("#")
    if len(raw) == 6 and re.match(r"^[0-9A-Fa-f]{6}$", raw):
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    if len(raw) == 3 and re.match(r"^[0-9A-Fa-f]{3}$", raw):
        return int(raw[0] * 2, 16), int(raw[1] * 2, 16), int(raw[2] * 2, 16)
    return default


def make_solid_jpeg_480(rgb: tuple[int, int, int] = (16, 23, 32)) -> bytes:
    """Synthesize a 100% ITU-T.81 baseline 480x480 RGB JPEG in pure Python stdlib."""
    r, g, b = (max(0, min(255, int(c))) for c in rgb)
    y = max(-128, min(127, round(0.299 * r + 0.587 * g + 0.114 * b) - 128))
    cb = max(-128, min(127, round(-0.168736 * r - 0.331264 * g + 0.5 * b)))
    cr = max(-128, min(127, round(0.5 * r - 0.418688 * g - 0.081312 * b)))

    # Quantization table of all 8s: DC_DCT = 8 * level => quantized DC = level
    qtable = bytes([8] * 64)

    def seg(marker: int, payload: bytes) -> bytes:
        return bytes([0xFF, marker]) + struct.pack("!H", len(payload) + 2) + payload

    app0 = seg(0xE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
    dqt0 = seg(0xDB, b"\x00" + qtable)
    dqt1 = seg(0xDB, b"\x01" + qtable)
    # SOF0 (Baseline DCT): 8-bit, height=480, width=480, 3 components (4:4:4 1x1 sampling)
    sof0 = seg(
        0xC0,
        struct.pack("!BHHB", 8, 480, 480, 3)
        + b"\x01\x11\x00"
        + b"\x02\x11\x01"
        + b"\x03\x11\x01",
    )
    dht = (
        seg(0xC4, b"\x00" + _STD_DC_LUMINANCE_BITS + _STD_DC_LUMINANCE_VALS)
        + seg(0xC4, b"\x10" + _MIN_AC_BITS + _MIN_AC_VALS)
        + seg(0xC4, b"\x01" + _STD_DC_CHROMINANCE_BITS + _STD_DC_CHROMINANCE_VALS)
        + seg(0xC4, b"\x11" + _MIN_AC_BITS + _MIN_AC_VALS)
    )
    sos_hdr = seg(0xDA, b"\x03\x01\x00\x02\x11\x03\x11\x00\x3F\x00")

    bit_acc = 0
    bit_len = 0
    scan = bytearray()

    def put_bits(val: int, nbits: int) -> None:
        nonlocal bit_acc, bit_len
        bit_acc = (bit_acc << nbits) | (val & ((1 << nbits) - 1))
        bit_len += nbits
        while bit_len >= 8:
            bit_len -= 8
            byte_out = (bit_acc >> bit_len) & 0xFF
            scan.append(byte_out)
            if byte_out == 0xFF:
                scan.append(0x00)

    def encode_dc(diff: int, table: dict[int, tuple[int, int]]) -> None:
        if diff == 0:
            code, clen = table[0]
            put_bits(code, clen)
            return
        abs_val = abs(diff)
        cat = abs_val.bit_length()
        code, clen = table[cat]
        put_bits(code, clen)
        mag = diff if diff > 0 else ((1 << cat) - 1 + diff)
        put_bits(mag, cat)

    # First 8x8 block (MCU 0 of 3600): encode actual DC + EOB (1-bit 0)
    encode_dc(y, _DC_LUM_CODES)
    put_bits(0, 1)  # AC EOB
    encode_dc(cb, _DC_CHR_CODES)
    put_bits(0, 1)  # AC EOB
    encode_dc(cr, _DC_CHR_CODES)
    put_bits(0, 1)  # AC EOB

    # Remaining 3599 8x8 blocks (60*60 - 1): diff=0 for all 3 channels + AC EOB (0)
    # Lum DC 0 = '00' (2b) + AC EOB = '0' (1b) -> '000' (3b)
    # Chr DC 0 = '00' (2b) + AC EOB = '0' (1b) -> '000' (3b) * 2
    # Total per block = 9 zero bits!
    total_zero_bits = 3599 * 9
    while total_zero_bits >= 16:
        put_bits(0, 16)
        total_zero_bits -= 16
    if total_zero_bits > 0:
        put_bits(0, total_zero_bits)

    if bit_len > 0:
        pad = 8 - bit_len
        put_bits((1 << pad) - 1, pad)

    return b"\xFF\xD8" + app0 + dqt0 + dqt1 + sof0 + dht + sos_hdr + bytes(scan) + b"\xFF\xD9"


def validate_baseline_jpeg_480(data: bytes) -> bool:
    """Verify `data` is a 480x480 8-bit 3-component baseline RGB JPEG <= 256 KiB."""
    if not isinstance(data, (bytes, bytearray)) or len(data) < 4 or len(data) > MAX_JPEG_BYTES:
        return False
    if data[0:2] != b"\xFF\xD8":
        return False
    i = 2
    n = len(data)
    found_sof0 = False
    while i + 1 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        while i < n and data[i] == 0xFF:
            i += 1
        if i >= n:
            break
        marker = data[i]
        i += 1
        if marker == 0xD9 or marker == 0xDA:  # EOI or SOS
            break
        if marker == 0x00 or (0xD0 <= marker <= 0xD7) or marker == 0x01:
            continue
        if i + 2 > n:
            return False
        seg_len = int.from_bytes(data[i : i + 2], "big")
        if seg_len < 2 or i + seg_len > n:
            return False
        if marker == 0xC2:  # Progressive JPEG rejected by firmware
            return False
        if marker == 0xC0:  # Baseline SOF0
            if seg_len < 17:
                return False
            precision = data[i + 2]
            height = int.from_bytes(data[i + 3 : i + 5], "big")
            width = int.from_bytes(data[i + 5 : i + 7], "big")
            components = data[i + 7]
            if precision != 8 or width != 480 or height != 480 or components != 3:
                return False
            found_sof0 = True
        i += seg_len
    return found_sof0


def _convert_file_to_480_jpeg(path: Path) -> bytes:
    """Convert any local image file to a 480x480 baseline RGB JPEG <= 256 KiB."""
    raw = path.read_bytes()
    if validate_baseline_jpeg_480(raw):
        return raw

    try:
        from PIL import Image, ImageOps  # type: ignore[import-not-found]
    except ImportError:
        Image = None  # type: ignore[assignment]

    if Image is not None and path.suffix.lower() != ".svg":
        with Image.open(path) as src:
            fitted = ImageOps.contain(ImageOps.exif_transpose(src).convert("RGB"), (480, 480))
            canvas = Image.new("RGB", (480, 480), "#0C0B0A")
            canvas.paste(fitted, ((480 - fitted.width) // 2, (480 - fitted.height) // 2))
            for quality in (90, 80, 65, 45, 25):
                buf = io.BytesIO()
                canvas.save(buf, format="JPEG", quality=quality, progressive=False, subsampling=2)
                candidate = buf.getvalue()
                if validate_baseline_jpeg_480(candidate):
                    return candidate
        raise ValueError("Image exceeds 256 KiB even after JPEG compression")

    if sys.platform == "darwin" and shutil.which("sips"):
        with tempfile.TemporaryDirectory(prefix="mosaico-canvas-") as tmp_dir:
            src_for_sips = path
            if path.suffix.lower() == ".svg" and shutil.which("qlmanage"):
                subprocess.run(
                    ["qlmanage", "-t", "-s", "480", "-o", tmp_dir, str(path.resolve())],
                    check=False,
                    capture_output=True,
                    timeout=15,
                )
                png_candidate = Path(tmp_dir) / (path.name + ".png")
                if png_candidate.exists():
                    src_for_sips = png_candidate

            out_jpg = Path(tmp_dir) / "canvas_480.jpg"
            for quality in (85, 70, 50, 30):
                subprocess.run(
                    [
                        "sips",
                        "-s",
                        "format",
                        "jpeg",
                        "-s",
                        "formatOptions",
                        str(quality),
                        "--resampleHeightWidthMax",
                        "480",
                        "--padToHeightWidth",
                        "480",
                        "480",
                        "--padColor",
                        "0C0B0A",
                        str(src_for_sips.resolve()),
                        "--out",
                        str(out_jpg),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=20,
                )
                candidate = out_jpg.read_bytes()
                if validate_baseline_jpeg_480(candidate):
                    return candidate

    raise ValueError(
        "Input image is not a 480x480 baseline RGB JPEG. "
        "Provide a 480x480 baseline JPEG, `solid:#RRGGBB`, or install `Pillow` (`pip install mosaico-mcp[image]`)."
    )


def prepare_canvas_jpeg(source: str | bytes) -> bytes:
    """Resolve `source` (bytes, `#RRGGBB`/`solid:#RRGGBB`, data URI, base64, URL, or file path)
    into a validated 480x480 baseline RGB JPEG <= 256 KiB.
    """
    if isinstance(source, (bytes, bytearray)):
        raw_bytes = bytes(source)
        if validate_baseline_jpeg_480(raw_bytes):
            return raw_bytes
        with tempfile.NamedTemporaryFile(prefix="mosaico-bytes-", suffix=".img", delete=False) as tf:
            tf.write(raw_bytes)
            tmp_path = Path(tf.name)
        try:
            return _convert_file_to_480_jpeg(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    text = str(source or "").strip()
    if not text:
        raise ValueError("Empty `image_source`")

    # 1. Pure-stdlib solid color canvas (`solid:#101720` or `#101720`)
    if text.lower().startswith("solid:"):
        return make_solid_jpeg_480(parse_hex_rgb(text.split(":", 1)[1]))
    if re.match(r"^#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?$", text):
        return make_solid_jpeg_480(parse_hex_rgb(text))

    # 2. Data URI (`data:image/jpeg;base64,...` or `data:image/svg+xml;base64,...`)
    if text.startswith("data:image/"):
        header, _, encoded = text.partition(",")
        if not encoded:
            raise ValueError("Invalid `data:image/...` URI")
        is_svg = "image/svg" in header.lower()
        decoded = base64.b64decode(encoded) if ";base64" in header.lower() else encoded.encode("utf-8")
        if not is_svg and validate_baseline_jpeg_480(decoded):
            return decoded
        suffix = ".svg" if is_svg else ".img"
        with tempfile.NamedTemporaryFile(prefix="mosaico-data-", suffix=suffix, delete=False) as tf:
            tf.write(decoded)
            tmp_path = Path(tf.name)
        try:
            return _convert_file_to_480_jpeg(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    # 3. HTTP / HTTPS image URL
    if text.startswith(("http://", "https://")):
        req = urllib.request.Request(text, headers={"User-Agent": "mosaico-mcp/2.0"})
        with _DIRECT_OPENER.open(req, timeout=8.0) as resp:
            downloaded = resp.read(2 * 1024 * 1024 + 1)
        if len(downloaded) > 2 * 1024 * 1024:
            raise ValueError("Remote image URL exceeded 2 MiB download cap")
        return prepare_canvas_jpeg(downloaded)

    # 4. Inline `<svg ...>` markup
    if text.lstrip().startswith("<svg"):
        with tempfile.NamedTemporaryFile(prefix="mosaico-svg-", suffix=".svg", delete=False) as tf:
            tf.write(text.encode("utf-8"))
            tmp_path = Path(tf.name)
        try:
            return _convert_file_to_480_jpeg(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    # 5. Local file path (check before base64 so paths like `/tmp/a.jpg` resolve cleanly)
    if len(text) <= 1024 and "\n" not in text:
        candidate_path = Path(text).expanduser()
        if candidate_path.exists() and candidate_path.is_file():
            return _convert_file_to_480_jpeg(candidate_path)

    # 6. Raw base64-encoded image string
    compact = "".join(text.split())
    if len(compact) >= 16 and len(compact) % 4 == 0 and re.match(r"^[A-Za-z0-9+/=]+$", compact):
        try:
            decoded = base64.b64decode(compact, validate=True)
            return prepare_canvas_jpeg(decoded)
        except Exception as exc:
            raise ValueError(f"Failed decoding base64 image: {exc}") from exc

    raise FileNotFoundError(f"Image file not found or unsupported `image_source`: {text[:120]}")
