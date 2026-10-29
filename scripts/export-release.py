#!/usr/bin/env python3
"""Export clean release firmware binary with checksums for GitHub Releases."""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Export release firmware binary and checksums")
    parser.add_argument("--version", default=None, help="Release version (defaults to project_description.json)")
    parser.add_argument("--output-dir", default=None, help="Output directory (defaults to dist/release-v<version>)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    app_dir = root / "vendor/esp-mosaico-vibe/projects/lan_screen"
    build_bin = app_dir / "build/lan_screen.bin"
    desc_file = app_dir / "build/project_description.json"

    if not build_bin.exists():
        sys.exit(f"Error: Build binary not found at {build_bin}. Please build the project first.")

    version = args.version
    if not version and desc_file.exists():
        try:
            desc = json.loads(desc_file.read_text(encoding="utf-8"))
            version = desc.get("project_version")
        except Exception:
            pass

    if not version or version == "unknown":
        # Fallback to CMakeLists.txt or Kconfig version if available
        cmake_file = app_dir / "CMakeLists.txt"
        if cmake_file.exists():
            import re
            m = re.search(r'PROJECT_VER\s+"([^"]+)"', cmake_file.read_text(encoding="utf-8"))
            if m:
                version = m.group(1)
    if not version:
        version = "1.1.54"

    if args.output_dir:
        out_dir = Path(args.output_dir).resolve()
    else:
        out_dir = root / "dist" / f"release-v{version}"
    out_dir.mkdir(parents=True, exist_ok=True)

    target_bin = out_dir / f"lan_screen_v{version}.bin"
    shutil.copy2(build_bin, target_bin)

    sha256 = hashlib.sha256(target_bin.read_bytes()).hexdigest()
    sums_file = out_dir / "SHA256SUMS"
    sums_file.write_text(f"{sha256}  {target_bin.name}\n", encoding="utf-8")

    size_mb = target_bin.stat().st_size / (1024 * 1024)

    print(f"=== Release Export Complete ===")
    print(f"Version:      v{version}")
    print(f"Artifact:     {target_bin}")
    print(f"Size:         {size_mb:.2f} MB ({target_bin.stat().st_size} bytes)")
    print(f"SHA-256:      {sha256}")
    print(f"\nUpload this file to your GitHub Release (https://github.com/jaypark0006/agent-friend/releases)!")

if __name__ == "__main__":
    main()
