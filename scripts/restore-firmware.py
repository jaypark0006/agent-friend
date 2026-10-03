#!/usr/bin/env python3
"""Restore committed local firmware history without overwriting an existing checkout."""
import argparse
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
firmware = root / 'vendor/esp-mosaico-vibe'
bundle = root / 'dependencies/esp-mosaico-vibe.bundle'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--skip-dependencies', action='store_true', help='restore only firmware Git history')
args = parser.parse_args()

def git(*arguments, cwd=root, capture=False):
    return subprocess.run(['git', *map(str, arguments)], cwd=cwd, check=True,
                          text=True, capture_output=capture)

entry = git('ls-files', '-s', 'vendor/esp-mosaico-vibe', capture=True).stdout.split()
if len(entry) < 2 or entry[0] != '160000':
    raise SystemExit('Root Git index has no firmware submodule reference.')
expected = entry[1]
if not (firmware / '.git').exists():
    if firmware.exists() and any(firmware.iterdir()):
        raise SystemExit('Firmware directory is nonempty; preserve it before restoration.')
    firmware.parent.mkdir(parents=True, exist_ok=True)
    git('clone', bundle, firmware)
    git('remote', 'set-url', 'origin', 'https://github.com/esp-mosaico/esp-mosaico-vibe.git', cwd=firmware)
else:
    git('fetch', bundle, 'refs/heads/main', cwd=firmware)
current = git('rev-parse', 'HEAD', cwd=firmware, capture=True).stdout.strip()
if current != expected:
    raise SystemExit(f'Existing HEAD {current} differs from committed {expected}; no checkout was overwritten.')
if not args.skip_dependencies:
    git('submodule', 'update', '--init', 'submodule/esp-mosaico-bsp',
        'submodule/esp-mosaico-utils', cwd=firmware)
print(f'Firmware ready at {current}. Pinned ESP-IDF and host LVGL setup are documented in the app README.')
