// All decoding, resizing and JPEG encoding runs in the host browser.
export const FRAME_WIDTH = 480;
export const FRAME_HEIGHT = 480;
export const MAX_JPEG_BYTES = 256 * 1024;

async function decodeImage(file) {
    if (typeof createImageBitmap === 'function') {
        try {
            const bitmap = await createImageBitmap(file, {imageOrientation: 'from-image'});
            return {image: bitmap, width: bitmap.width, height: bitmap.height,
                close: () => bitmap.close()};
        } catch (_) {
            // Some browser formats only work through HTMLImageElement.
        }
    }
    const url = URL.createObjectURL(file);
    try {
        const image = new Image();
        await new Promise((resolve, reject) => {
            image.onload = resolve;
            image.onerror = () => reject(new Error('浏览器无法解码这张图片；HEIC 等格式如不受支持，请先转换为 JPEG 或 PNG。'));
            image.src = url;
        });
        return {image, width: image.naturalWidth, height: image.naturalHeight,
            close: () => { image.src = ''; URL.revokeObjectURL(url); }};
    } catch (error) {
        URL.revokeObjectURL(url);
        throw error;
    }
}

function encodeJpeg(canvas, quality) {
    return new Promise((resolve, reject) => canvas.toBlob(blob => {
        if (!blob || blob.type !== 'image/jpeg') {
            reject(new Error('浏览器未能生成 JPEG 图片。'));
        } else {
            resolve(blob);
        }
    }, 'image/jpeg', quality));
}

// Canvas JPEG settings differ across browsers. Check the output rather than
// assuming every encoder uses the device's baseline, RGB and size constraints.
export async function checkFrameJpeg(blob) {
    if (!blob.size || blob.size > MAX_JPEG_BYTES) throw new Error('转换后的图片超过 256 KiB。');
    const bytes = new Uint8Array(await blob.arrayBuffer());
    const word = at => (bytes[at] << 8) | bytes[at + 1];
    if (bytes.length < 4 || word(0) !== 0xffd8 || word(bytes.length - 2) !== 0xffd9) {
        throw new Error('浏览器生成的图片不是完整 JPEG。');
    }
    let at = 2, foundFrame = false;
    while (at < bytes.length) {
        if (bytes[at++] !== 0xff) break;
        while (bytes[at] === 0xff) at++;
        const marker = bytes[at++];
        if (marker === 0xda) {
            if (foundFrame) return;
            break;
        }
        if (marker === 0xd9) break;
        if (marker === 0x01 || (marker >= 0xd0 && marker <= 0xd8)) continue;
        if (at + 2 > bytes.length) break;
        const length = word(at);
        if (length < 2 || at + length > bytes.length) break;
        const isFrame = marker >= 0xc0 && marker <= 0xcf &&
            marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc;
        if (isFrame) {
            if (marker !== 0xc0 || length < 17 || bytes[at + 2] !== 8 ||
                word(at + 3) !== FRAME_HEIGHT || word(at + 5) !== FRAME_WIDTH || bytes[at + 7] !== 3) {
                throw new Error('浏览器的 JPEG 编码不符合设备要求（480×480、8-bit、三分量 baseline）。');
            }
            foundFrame = true;
        }
        at += length;
    }
    throw new Error('无法识别浏览器生成的 JPEG 图片。');
}

export async function prepareImage(file, {fit = 'contain', background = '#101720'} = {}) {
    if (!(file instanceof Blob) || !file.size) throw new Error('请先选择一张图片。');
    if (fit !== 'contain' && fit !== 'cover') throw new Error('不支持的图片布局。');
    const decoded = await decodeImage(file);
    const canvas = document.createElement('canvas');
    canvas.width = FRAME_WIDTH; canvas.height = FRAME_HEIGHT;
    try {
        if (!decoded.width || !decoded.height) throw new Error('图片尺寸无效。');
        const context = canvas.getContext('2d', {alpha: false});
        if (!context) throw new Error('浏览器不支持图片转换。');
        context.fillStyle = background;
        context.fillRect(0, 0, FRAME_WIDTH, FRAME_HEIGHT);
        context.imageSmoothingEnabled = true;
        context.imageSmoothingQuality = 'high';
        if (fit === 'cover') {
            const side = Math.min(decoded.width, decoded.height);
            context.drawImage(decoded.image, (decoded.width - side) / 2, (decoded.height - side) / 2,
                side, side, 0, 0, FRAME_WIDTH, FRAME_HEIGHT);
        } else {
            const scale = Math.min(FRAME_WIDTH / decoded.width, FRAME_HEIGHT / decoded.height);
            const width = decoded.width * scale, height = decoded.height * scale;
            context.drawImage(decoded.image, (FRAME_WIDTH - width) / 2, (FRAME_HEIGHT - height) / 2, width, height);
        }
        let quality = 0.95, blob = await encodeJpeg(canvas, quality);
        if (blob.size > MAX_JPEG_BYTES) {
            let low = 0.10, high = quality;
            blob = await encodeJpeg(canvas, low); quality = low;
            if (blob.size > MAX_JPEG_BYTES) throw new Error('图片无法压缩到 256 KiB 内。');
            // Keep the best candidate that actually fits, even if an encoder's
            // size changes are not strictly monotonic at quantization steps.
            for (let pass = 0; pass < 7; pass++) {
                const candidateQuality = (low + high) / 2;
                const candidate = await encodeJpeg(canvas, candidateQuality);
                if (candidate.size <= MAX_JPEG_BYTES) {
                    blob = candidate; quality = candidateQuality; low = candidateQuality;
                } else {
                    high = candidateQuality;
                }
            }
        }
        await checkFrameJpeg(blob);
        return {blob, quality, width: FRAME_WIDTH, height: FRAME_HEIGHT,
            sourceWidth: decoded.width, sourceHeight: decoded.height};
    } finally {
        decoded.close();
        canvas.width = 0; canvas.height = 0;
    }
}
