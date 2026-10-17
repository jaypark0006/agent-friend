#!/usr/bin/env python3
"""Generate independent square4 diffuser inserts; no source-shell edits or slicing.

Units: mm. Centre membrane is 0.40 thick; rim alone reaches 1.20 overall.
Print broad flat flange on bed. Install raised locator towards front aperture.
"""
import argparse
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
ARC_SEGMENTS = 28


def outline(width, length, radius, cx=0, cy=0):
    """CCW rounded rectangle about a common centre."""
    centres = [(width/2-radius, -length/2+radius, -90),
               (width/2-radius, length/2-radius, 0),
               (-width/2+radius, length/2-radius, 90),
               (-width/2+radius, -length/2+radius, 180)]
    pts = []
    for x,y,start in centres:
        for i in range(ARC_SEGMENTS+1):
            a = math.radians(start+90*i/ARC_SEGMENTS)
            pts.append((cx+x+radius*math.cos(a), cy+y+radius*math.sin(a)))
    return pts


def insert(membrane=0.40, locator_height=0.80, locator_gap=0.10):
    """One closed mesh: thin flange/membrane plus a hollow locating rim."""
    fw,fl,fr = 9.25,9.85,0.80
    lw,ll,lr = 8.05-2*locator_gap,8.15-2*locator_gap,0.95-locator_gap
    wall=0.50
    base_chamfer=0.05
    lead_in=0.10
    lead_height=0.20
    top=membrane+locator_height
    bottom=outline(fw-2*base_chamfer,fl-2*base_chamfer,fr-base_chamfer)
    flange=outline(fw,fl,fr)
    locator=outline(lw,ll,lr)
    tip=outline(lw-2*lead_in,ll-2*lead_in,lr-lead_in)
    inner=outline(lw-2*wall,ll-2*wall,lr-wall)
    profiles=[(bottom,0),(flange,base_chamfer),(flange,membrane),
              (locator,membrane),(locator,top-lead_height),(tip,top),
              (inner,membrane),(inner,top)]
    n=len(bottom)
    vertices=[(x+fw/2,y+fl/2,z) for p,z in profiles for x,y in p]
    vertices.extend([(fw/2,fl/2,0),(fw/2,fl/2,membrane)])
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces.extend([(8*n,j,i),(8*n+1,6*n+i,6*n+j)])
        # Outside walls, with counterclockwise loops viewed from above.
        for a,b in [(0,1),(1,2),(3,4),(4,5)]:
            faces.extend([(a*n+i,a*n+j,b*n+j),(a*n+i,b*n+j,b*n+i)])
        # Exposed upward annuli: flange top and locator rim top.
        for a,b in [(2,3),(5,7)]:
            faces.extend([(a*n+i,a*n+j,b*n+j),(a*n+i,b*n+j,b*n+i)])
        # Inward normal on the hollow locator's inner wall.
        faces.extend([(6*n+i,7*n+j,6*n+j),(6*n+i,7*n+i,7*n+j)])
    dimensions=dict(flange_width_mm=fw,flange_length_mm=fl,
        flange_corner_radius_mm=fr,membrane_thickness_mm=membrane,
        locator_outer_width_mm=lw,locator_outer_length_mm=ll,
        locator_corner_radius_mm=lr,locator_wall_mm=wall,
        locator_height_mm=locator_height,overall_height_mm=top,
        locator_clearance_per_side_mm=locator_gap,
        flange_clearance_per_side_mm=0.15,
        lead_in_per_side_mm=lead_in,lead_in_height_mm=lead_height,
        forward_overlap_per_side_x_mm=0.60,forward_overlap_per_side_y_mm=0.85,
        install_direction='Raised locator faces the front aperture; flange rests on rear ledge.',
        rearward_snap_lock=False)
    return vertices,faces,dimensions


def stl(path, vertices, faces):
    with path.open('wb') as stream:
        stream.write(b'Mosaico LED diffuser; mm; white PLA'.ljust(80, b'\0'))
        stream.write(struct.pack('<I', len(faces)))
        for face in faces:
            a,b,c = [vertices[i] for i in face]
            u = [b[i]-a[i] for i in range(3)]
            v = [c[i]-a[i] for i in range(3)]
            normal = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
            mag = math.sqrt(sum(q*q for q in normal))
            normal = [q/mag for q in normal]
            stream.write(struct.pack('<12fH', *normal, *a, *b, *c, 0))


def three_mf(path, parts):
    ET.register_namespace('', CORE)
    def el(parent, tag, **attrs):
        return ET.SubElement(parent, '{'+CORE+'}'+tag, {k:str(v) for k,v in attrs.items()})
    root = ET.Element('{'+CORE+'}model', unit='millimeter')
    el(root, 'metadata', name='Title').text = 'ESP-Mosaico square4 V3 separate locating diffuser objects'
    resources = el(root, 'resources')
    material = el(resources, 'basematerials', id=1)
    el(material, 'base', name='White PLA', displaycolor='#FFFFFFFF')
    build = el(root, 'build')
    for idx, (name, vertices, faces) in enumerate(parts):
        obj = el(resources, 'object', id=idx+2, type='model', name=name, pid=1, pindex=0)
        mesh = el(obj, 'mesh')
        vs = el(mesh, 'vertices')
        for x,y,z in vertices:
            el(vs, 'vertex', x=f'{x:.7f}', y=f'{y:.7f}', z=f'{z:.7f}')
        fs = el(mesh, 'triangles')
        for a,b,c in faces:
            el(fs, 'triangle', v1=a, v2=b, v3=c)
        x, y = 40+(idx%2)*16, 40+(idx//2)*18
        el(build, 'item', objectid=idx+2, transform=f'1 0 0 0 1 0 0 0 1 {x} {y} 0')
    types = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
    rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as package:
        package.writestr('[Content_Types].xml', types)
        package.writestr('_rels/.rels', rels)
        package.writestr('3D/3dmodel.model', ET.tostring(root, encoding='utf-8', xml_declaration=True))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--membrane',type=float,default=0.40)
    p.add_argument('--locator-height',type=float,default=0.80)
    p.add_argument('--locator-gap',type=float,default=0.10)
    p.add_argument('--out',type=Path,default=Path(__file__).parent/'print-files')
    a=p.parse_args()
    if not (0.20<=a.membrane<=0.60 and 0.40<=a.locator_height<=1.20 and 0.05<=a.locator_gap<=0.20):
        p.error('Require membrane 0.20..0.60, locator height 0.40..1.20, locator gap 0.05..0.20 mm')
    a.out.mkdir(parents=True,exist_ok=True)
    vertices,faces,dimensions=insert(a.membrane,a.locator_height,a.locator_gap)
    stl(a.out/'square4_v3_locating_diffuser_1pc.stl',vertices,faces)
    parts=[(f'{i+1:02d}_independent_locating_diffuser',vertices,faces) for i in range(4)]
    three_mf(a.out/'square4_v3_locating_diffusers_4_objects.3mf',parts)
    (a.out/'dimensions.json').write_text(json.dumps(dict(revision='V3',
        independent_objects=4,identical_parts=True,source_shell_modified=False,
        dimensions=dimensions),ensure_ascii=False,indent=2)+'\n')
    print('Generated one standalone STL and a 3MF with four independent inserts:',a.out)


if __name__=='__main__':
    main()
