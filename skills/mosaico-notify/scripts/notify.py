#!/usr/bin/env python3
"""Local macOS discovery, identity checked delivery, no mutation retries."""
import argparse
import concurrent.futures
import datetime
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

MAC = '1c:29:04:d0:ad:2a'
CACHE = Path.home() / '.cache/mosaico-notify/address.json'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

def command(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=3).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ''

def neighbors():
    result = {}
    for ip, mac in re.findall(r'\((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-f:]+)', command('/usr/sbin/arp', '-an')):
        parts = mac.split(':')
        if len(parts) == 6:
            result[ip] = ':'.join(p.zfill(2) for p in parts)
    return result

def request(ip, path, body=None, mime='application/json', timeout=3):
    ipaddress.IPv4Address(ip)
    req = urllib.request.Request('http://' + ip + path, data=body,
                                 headers={'Content-Type': mime}, method='GET' if body is None else 'POST')
    with HTTP.open(req, timeout=timeout) as response:
        raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError('oversized response')
        return json.loads(raw)

def identify(ip):
    try:
        info = request(ip, '/api/info', timeout=0.8)
        return ip if info.get('app') == 'lan_screen' and neighbors().get(ip) == MAC else None
    except Exception:
        return None

def discover(explicit):
    candidates = [explicit] if explicit else []
    candidates += [ip for ip, mac in neighbors().items() if mac == MAC]
    try:
        candidates.append(json.loads(CACHE.read_text())['ip'])
    except (OSError, ValueError, KeyError):
        pass
    candidates.append('192.168.5.61')
    for ip in dict.fromkeys(x for x in candidates if x):
        if identify(ip):
            return ip
    route = command('/sbin/route', '-n', 'get', 'default')
    match = re.search(r'interface:\s*(\S+)', route)
    if match:
        interface = match.group(1)
        address = command('/usr/sbin/ipconfig', 'getifaddr', interface).strip()
        mask = command('/usr/sbin/ipconfig', 'getoption', interface, 'subnet_mask').strip()
        try:
            network = ipaddress.IPv4Network(address + '/' + mask, strict=False)
        except ValueError:
            network = None
        if network and network.is_private and network.num_addresses <= 256:
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
                matches = [x for x in pool.map(identify, (str(h) for h in network.hosts())) if x]
            if len(matches) == 1:
                return matches[0]
    raise RuntimeError('未找到身份匹配的随身屏；确认同一局域网，或通过 --ip 提供当前地址。')

def card(args):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    font_path = next((str(p) for p in [
        Path('/System/Library/Fonts/PingFang.ttc'),
        Path('/System/Library/Fonts/STHeiti Medium.ttc'),
        Path('/System/Library/Fonts/STHeiti Light.ttc')
    ] if p.exists()), None)
    if not font_path:
        raise RuntimeError('缺少可用中文字体，请配置本机中文字体路径')
    def font(size):
        return ImageFont.truetype(font_path, size)
    im = Image.new('RGB', (480, 480), '#101820')
    d = ImageDraw.Draw(im)
    color = {'done':'#59e3ab', 'error':'#ff807b', 'attention':'#ffd16b'}[args.status]
    d.rounded_rectangle((24, 24, 456, 456), radius=26, outline='#354655', width=2)
    d.text((44, 40), 'CODEX  /  ' + args.status.upper(), font=font(20), fill=color)
    if args.image:
        with Image.open(args.image) as source:
            image = ImageOps.contain(ImageOps.exif_transpose(source).convert('RGB'), (392, 170))
            im.paste(image, ((480-image.width)//2, 83+(170-image.height)//2))
    else:
        d.ellipse((192, 100, 288, 196), outline=color, width=5)
        if args.status == 'done':
            d.line([(213,147),(234,166),(269,126)], fill=color, width=7)
        else:
            d.line((240,121,240,155), fill=color, width=6)
            d.ellipse((237,168,243,174), fill=color)
    def wrapped(text, y, size, lines, fill):
        f = font(size); rows=[]; line=''
        for ch in text:
            if ch == '\n' or d.textlength(line+ch, font=f) > 388:
                rows.append(line); line='' if ch=='\n' else ch
            else:
                line += ch
        rows.append(line)
        clipped = len(rows)>lines
        rows=rows[:lines]
        if clipped:
            rows[-1]=rows[-1][:-1]+'…'
        for row in rows:
            d.text((44,y),row,font=f,fill=fill); y+=size+8
    wrapped(args.title, 264, 30, 2, '#ffffff')
    wrapped(args.text, 346, 19, 3, '#bacbd6')
    d.text((44,429),datetime.datetime.now().astimezone().strftime('%m-%d  %H:%M'),font=font(15),fill=color)
    for quality in (90,80,65,45):
        out=io.BytesIO(); im.save(out,format='JPEG',quality=quality,progressive=False,subsampling=2)
        if len(out.getvalue())<=262144:
            return out.getvalue()
    raise ValueError('JPEG exceeds device size limit')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--title',required=True); p.add_argument('--text',required=True)
    p.add_argument('--status',choices=['done','error','attention'],default='done')
    p.add_argument('--image'); p.add_argument('--ip'); p.add_argument('--keep-view',action='store_true')
    args=p.parse_args(); results={}
    try:
        text=args.title+'\n'+args.text
        if len(text.encode('utf-8'))>1024:
            raise ValueError('title + text must be <=1024 UTF-8 bytes')
        jpeg=card(args)
        ip=discover(args.ip); results['ip']=ip
        CACHE.parent.mkdir(parents=True,exist_ok=True)
        temp=CACHE.with_name('address.'+str(os.getpid())+'.tmp')
        temp.write_text(json.dumps({'ip':ip,'mac':MAC})); temp.replace(CACHE)
        def post(path, value):
            return request(ip,path,json.dumps(value,ensure_ascii=False).encode('utf-8'))
        results['text']=post('/api/text',{'text':text,'font_size':28,'align':'left','time':datetime.datetime.now().strftime('%H:%M')})
        if not isinstance(results['text'].get('accepted'),int):
            raise RuntimeError('文字未返回accepted，停止后续推送')
        results['image']=request(ip,'/api/frame',jpeg,'image/jpeg',timeout=8)
        if not isinstance(results['image'].get('accepted'),int):
            raise RuntimeError('图片未返回accepted，停止切页')
        if not args.keep_view:
            results['view']=post('/api/view',{'page':'image'})
        results['delivery']='accepted; not a display/read confirmation'
        print(json.dumps(results,ensure_ascii=False)); return 0
    except Exception as exc:
        results['error']=str(exc); results['note']='不自动重试；已列出的步骤可能已接收，超时步骤结果未知。'
        print(json.dumps(results,ensure_ascii=False),file=sys.stderr); return 1
if __name__=='__main__':
    sys.exit(main())
