#!/usr/bin/env python3
"""Control ESP-Mosaico interaction subboard LEDs and trigger preset animations."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from notify import discover, request

def hex_to_rgb(hex_str):
    h = hex_str.lstrip('#')
    if len(h) == 6:
        return [int(h[i:i+2], 16) for i in (0, 2, 4)]
    elif len(h) == 3:
        return [int(h[i]*2, 16) for i in range(3)]
    return [57, 230, 157]

def main():
    p = argparse.ArgumentParser(description="Control Mosaico subboard LED preset animations")
    p.add_argument("--effect", choices=["breathe", "chase", "marquee", "rainbow", "alert", "warning", "success", "solid", "off"], default="breathe", help="Preset LED animation effect")
    p.add_argument("--color", default="#4fa3e3", help="Base color in hex (e.g. #4fa3e3)")
    p.add_argument("--speed", type=int, default=None, help="Animation cycle period in milliseconds")
    p.add_argument("--brightness", type=int, default=32, help="Brightness 0..64 (default: 32)")
    p.add_argument("--slot", default="right", choices=["left", "right"], help="Subboard slot (default: right)")
    p.add_argument("--off", action="store_true", help="Turn off all LEDs immediately")
    p.add_argument("--ip", default=None, help="Device IP candidate")
    args = p.parse_args()

    ip = discover(args.ip)
    if not ip:
        print("Device not found on local network", file=sys.stderr)
        sys.exit(1)

    payload = {
        "slot": args.slot,
        "brightness": min(64, max(0, args.brightness))
    }

    if args.off:
        payload["effect"] = "off"
    else:
        payload["effect"] = args.effect
        if args.color and args.effect not in ["rainbow", "off"]:
            payload["color"] = hex_to_rgb(args.color)
        if args.speed:
            payload["speed"] = args.speed

    try:
        res = request(ip, "/api/interact/leds", json.dumps(payload).encode("utf-8"), timeout=3)
        print(json.dumps({"ip": ip, "led": res, "effect": payload["effect"]}))
    except Exception as e:
        print(f"Error controlling LEDs: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
