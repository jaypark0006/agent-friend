#!/usr/bin/env python3
"""Refresh the portable Git bundle after committing firmware source changes."""
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[1]
firmware = root / 'vendor/esp-mosaico-vibe'
if subprocess.check_output(['git', 'status', '--porcelain'], cwd=firmware, text=True).strip():
    raise SystemExit('Commit firmware changes before creating its bundle.')
bundle = root / 'dependencies/esp-mosaico-vibe.bundle'
bundle.parent.mkdir(exist_ok=True)
subprocess.run(['git', 'bundle', 'create', str(bundle), 'main'], cwd=firmware, check=True)
subprocess.run(['git', 'bundle', 'verify', str(bundle)], cwd=firmware, check=True)
print('Commit the refreshed bundle and firmware submodule reference in the root repository.')
