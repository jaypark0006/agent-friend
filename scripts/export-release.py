#!/usr/bin/env python3
"""Export clean release firmware binary with checksums for GitHub Releases."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
app_dir = root / "vendor/esp-mosaico-vibe/projects/lan_screen"
build_bin = app_dir / "build/lan_screen.bin"
desc_file = app_dir / "build/project_description.json"

if not build_bin.exists():
    sys.exit(f"Error: Build binary not found at {build_bin}. Please build the project first.")

version = "unknown"
if desc_file.exists():
    try:
        desc = json.loads(desc_file.read_text(encoding="utf-8"))
        version = desc.get("project_version", "unknown")
    except Exception:
        pass

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
