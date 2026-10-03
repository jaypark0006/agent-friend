#!/usr/bin/env python3
"""Display a completion JPEG, wait after LCD completion, then display a photo."""
import argparse
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--host', required=True)
parser.add_argument('--completed', type=Path, required=True)
parser.add_argument('--photo', type=Path, required=True)
parser.add_argument('--hold', type=float, default=3.0)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if not 0 <= args.hold <= 60:
    parser.error('--hold must be between 0 and 60 seconds')
base = 'http://' + args.host

def status():
    with urlopen(base + '/api/status', timeout=5) as response:
        return json.load(response)

def push(path):
    jpeg = path.read_bytes()
    if not 4 <= len(jpeg) <= 262144:
        raise ValueError(f'{path}: invalid JPEG byte count')
    before = status()
    request = Request(base + '/api/frame', data=jpeg, headers={'Content-Type': 'image/jpeg'}, method='POST')
    with urlopen(request, timeout=5) as response:
        ack = json.load(response)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        current = status()
        if current['received'] > ack['accepted']:
            raise RuntimeError('Another sender is active; cannot confirm this image remained on screen.')
        if current['invalid'] > before['invalid']:
            raise RuntimeError('Device reported a JPEG decoding error.')
        if current['displayed'] > before['displayed']:
            return {'file': str(path), 'jpeg_bytes': len(jpeg), 'ack': ack,
                    'displayed_before': before['displayed'], 'displayed_after': current['displayed'],
                    'display_completed': True, 'device_timestamp_us': current['timestamp_us']}
        time.sleep(0.1)
    raise TimeoutError('No LCD completion within 10 seconds. Return the device to its main display page.')

result = {'host': args.host, 'hold_requested_seconds': args.hold, 'steps': []}
try:
    result['steps'].append(push(args.completed))
    print('Completion interface displayed; holding...', flush=True)
    hold_started = time.monotonic()
    time.sleep(args.hold)
    result['actual_hold_seconds'] = round(time.monotonic() - hold_started, 3)
    result['steps'].append(push(args.photo))
    result['success'] = True
finally:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
