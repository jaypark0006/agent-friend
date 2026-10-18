#!/usr/bin/env python3
"""Draw a source-mesh comparison and a delivery card; no slicer or app used."""
import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).parent
FONT='/System/Library/Fonts/STHeiti Light.ttc'

def text(d,x,y,value,size=24,color='#22364a'):
    d.text((x,y),value,font=ImageFont.truetype(FONT,size),fill=color)


def load_mesh(path,member):
    with zipfile.ZipFile(path) as package:r=ET.fromstring(package.read(member))
    v=np.array([[float(p.get(k)) for k in ('x','y','z')] for p in r.findall('.//{*}vertex')])
    f=np.array([[int(p.get(k)) for k in ('v1','v2','v3')] for p in r.findall('.//{*}triangle')])
    return v,f


def rounded_points(cx,cy,w,h,r):
    pts=[]
    for x,y,a in [(cx+w/2-r,cy-h/2+r,-90),(cx+w/2-r,cy+h/2-r,0),
                  (cx-w/2+r,cy+h/2-r,90),(cx-w/2+r,cy-h/2+r,180)]:
        for i in range(29):
            rad=math.radians(a+90*i/28);pts.append((x+r*math.cos(rad),y+r*math.sin(rad)))
    return pts


def draw_front(d,v,f,cx,cy,scale,highlight=False):
    # Orthographic outside/front view, looking towards +Z.
    proj=lambda p:(cx+p[0]*scale,cy-p[1]*scale)
    tris=v[f]
    n=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0])
    idx=np.flatnonzero(n[:,2]<-1e-12)
    idx=idx[np.argsort(-tris[idx,:,2].mean(1))]
    for i in idx:
        normal=n[i]/np.linalg.norm(n[i])
        light=.72+.23*max(0,-normal[2])+.03*normal[0]
        color=tuple(int(c*light) for c in (247,249,252))
        d.polygon([proj(p) for p in tris[i]],fill=color)
    if highlight:
        for y in [16.88247,5.62749,-5.62749,-16.88247]:
            pts=[proj((x,yy,0)) for x,yy in rounded_points(-16.8875,y,9.25,9.35,1.55)]
            d.polygon(pts,fill='#b2e2f2',outline='#258bab',width=2)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path.home()/'Downloads/ESP-Mosaico_Module_Interaction_square4-3D.3mf')
    args=p.parse_args()
    before,before_f=load_mesh(args.source,'3D/Objects/object_5.model')
    after,after_f=load_mesh(ROOT/'print-files/square4_front_integrated_diffuser_040mm.3mf','3D/3dmodel.model')
    im=Image.new('RGB',(1200,1030),'#f2f6fa');d=ImageDraw.Draw(im)
    text(d,38,26,'直接改原前壳 · 四窗一体均光薄膜',37)
    text(d,38,85,'基于 square4-3D.3mf；新增薄面与前壳连在一起，无需装小片。',24,'#63778b')
    for x1,x2 in [(25,585),(610,1175)]:
        d.rounded_rectangle((x1,142,x2,690),radius=18,fill='#dce4ec')
    text(d,48,162,'原前壳：四处贯通灯孔',26)
    text(d,633,162,'修改后：四处 0.40 mm 薄面',26)
    draw_front(d,before,before_f,305,443,9.1)
    draw_front(d,after,after_f,892,443,9.1,True)
    text(d,48,640,'外侧视图；孔后没有均光件',21,'#526a81')
    text(d,633,640,'蓝色仅突出新增区域，实际可全白打印',20,'#526a81')
    d.rounded_rectangle((25,720,1175,970),radius=18,fill='white')
    text(d,48,741,'打印方向：正面贴平台，内腔朝上',27)
    # Diagram of two body walls above a film starting on the build plate.
    d.rectangle((67,901,551,918),fill='#60768a')
    d.rectangle((104,877,514,901),fill='#8dd1e7',outline='#1683a6',width=2)
    d.rectangle((104,804,165,877),fill='#d4dce6',outline='#8b9eb3',width=2)
    d.rectangle((453,804,514,877),fill='#d4dce6',outline='#8b9eb3',width=2)
    text(d,202,821,'内腔朝上',24,'#63778b')
    text(d,185,929,'打印平台',20,'#526a81')
    text(d,600,807,'均光面从 Z=0 开始，直接由平台承托。',23)
    text(d,600,851,'0.20 mm 首层 + 0.20 mm 第二层。',23)
    text(d,600,895,'这四个新增薄面无需支撑。',24,'#087ea4')
    text(d,38,992,'2026-10-19 / 未切片、未试打、未实物装配或透光验证。',21,'#63778b')
    im.save(ROOT/'shell-change-and-print-orientation.png')
    card=Image.new('RGB',(480,480),'#101a27');c=ImageDraw.Draw(card)
    text(c,22,17,'CODEX · 前壳改造交付',21,'#78d6ee')
    text(c,22,58,'一体均光薄膜 · 0.40 mm',26,'#eef7ff')
    c.rounded_rectangle((17,109,463,341),radius=15,fill='#dce4ec')
    draw_front(c,after,after_f,240,225,4.8,True)
    text(c,22,359,'正面朝下打印 · 不再安装四小片',21,'#98deef')
    text(c,22,402,'已生成完整前壳 STL / 3MF',21,'#eef7ff')
    text(c,22,444,'未切片或打印验证 · 2026-10-19',18,'#ffd18a')
    card.save(ROOT/'delivery-receipt.png')
    with zipfile.ZipFile(ROOT/'square4-integrated-shell-diffuser-040mm.zip','w',zipfile.ZIP_DEFLATED) as package:
        for path in sorted(ROOT.rglob('*')):
            if path.is_file() and path.suffix not in ['.zip','.pyc'] and '__pycache__' not in path.parts:
                package.write(path,'square4-integrated-shell-diffuser-040mm/'+str(path.relative_to(ROOT)))
    print('Generated source comparison, print-direction illustration, receipt and delivery ZIP.')


if __name__=='__main__':main()
