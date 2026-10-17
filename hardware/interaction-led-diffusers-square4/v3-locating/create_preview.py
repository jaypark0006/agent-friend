#!/usr/bin/env python3
"""Draw a geometry illustration and delivery receipt (requires Pillow)."""
import json
import math
from pathlib import Path
import zipfile
from PIL import Image, ImageDraw, ImageFont
from generate import insert

ROOT=Path(__file__).parent
FONT='/System/Library/Fonts/STHeiti Light.ttc'

def text(draw,x,y,value,size=24,color='#24354a'):
    draw.text((x,y),value,font=ImageFont.truetype(FONT,size),fill=color)


def model(draw,cx,cy,scale):
    vertices,faces,_=insert()
    def project(p):
        x,y,z=p
        x-=9.25/2;y-=9.85/2
        return (cx+(x-y)*scale*.85,cy+(x+y)*scale*.40-z*scale*1.4)
    def face_depth(face):
        return sum(vertices[i][0]+vertices[i][1]+2*vertices[i][2] for i in face)/3
    for face in sorted(faces,key=face_depth):
        a,b,c=[vertices[i] for i in face]
        u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
        n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        if n[0]+n[1]+2*n[2]<=0:continue
        mag=math.sqrt(sum(x*x for x in n));n=[x/mag for x in n]
        shade=.65+.30*max(0,(n[0]*.3+n[1]*.15+n[2]*.9))
        rgb=tuple(int(x*shade) for x in [210,239,250])
        draw.polygon([project(vertices[i]) for i in face],fill=rgb)


def main():
    im=Image.new('RGB',(1200,870),'#f4f7fa');d=ImageDraw.Draw(im)
    text(d,40,25,'square4 · 独立定位均光件 × 4',38)
    text(d,40,83,'原外壳保持不变，只打印这四个新增对象。',25,'#5c6f84')
    d.rounded_rectangle((25,140,680,650),radius=18,fill='white')
    d.rounded_rectangle((700,140,1175,650),radius=18,fill='white')
    text(d,48,163,'单件结构：薄面、定位圈、挡边连成一体',23)
    model(d,350,408,32)
    text(d,62,565,'外侧挡边：9.25 × 9.85 mm',25,'#087ea4')
    text(d,62,606,'四件完全相同；每件都是一个独立对象',22)
    text(d,723,163,'剖面示意（不是同比例）',24)
    # Install front down: membrane on rear ledge, locator projects into aperture.
    d.rectangle((746,327,1130,353),fill='#95d7ec',outline='#087ea4',width=2)
    d.rectangle((800,353,818,425),fill='#95d7ec',outline='#087ea4',width=2)
    d.rectangle((1058,353,1076,425),fill='#95d7ec',outline='#087ea4',width=2)
    d.polygon([(734,353),(793,353),(793,467),(734,467)],fill='#b9c5d3')
    d.polygon([(1083,353),(1142,353),(1142,467),(1083,467)],fill='#b9c5d3')
    text(d,797,236,'内部 / LED 侧',23,'#6b7f96')
    text(d,821,383,'圈内是空的',20)
    text(d,827,474,'朝正面小孔',22,'#6b7f96')
    text(d,723,548,'中央透光面：0.40 mm',25,'#087ea4')
    text(d,723,589,'周圈高 0.80；最高处 1.20 mm',22)
    text(d,40,688,'定位圈外形 7.85 × 7.95 mm，单边间隙 0.10 mm，入口有倒角。',24)
    text(d,40,734,'大平面贴平台打印；安装时圈朝正面，挡边从内部落在原台阶上。',23)
    text(d,40,797,'2026-10-17 / 已生成模型；未做实物装配或透光测试。',22,'#6b7f96')
    im.save(ROOT/'structure-and-installation.png')
    card=Image.new('RGB',(480,480),'#101a27');c=ImageDraw.Draw(card)
    text(c,25,20,'CODEX · 新增独立对象',21,'#78d6ee')
    text(c,25,63,'定位均光件 × 4',29,'#f0f7ff')
    c.rounded_rectangle((20,118,460,321),radius=15,fill='#f1f6fa')
    model(c,240,241,20)
    text(c,25,339,'薄面 0.40 mm + 中空定位圈',22,'#a5e9f7')
    text(c,25,380,'原外壳不改 · 3MF / STL 已生成',20,'#e3edf8')
    text(c,25,434,'尚未实装或透光验证',20,'#ffd18a')
    card.save(ROOT/'delivery-receipt.png')
    source=json.loads((ROOT.parent/'source-measurements.json').read_text())
    _,_,dims=insert()
    source.update(revision='V3 2026-10-17',design_dimensions=dims,
        independent_objects=4,source_shell_modified=False,
        physical_fit_verified=False,optical_performance_verified=False)
    (ROOT/'source-measurements.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(ROOT/'square4-v3-independent-locating-diffusers.zip','w',zipfile.ZIP_DEFLATED) as package:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and p.suffix not in ['.zip','.pyc'] and '__pycache__' not in p.parts:
                package.write(p,'square4-v3-independent-locating-diffusers/'+str(p.relative_to(ROOT)))
    print('Generated structure drawing, receipt image and V3 ZIP.')


if __name__=='__main__':
    main()
