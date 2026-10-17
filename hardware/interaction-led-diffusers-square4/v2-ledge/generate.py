#!/usr/bin/env python3
"""Generate four thin LED diffusers seated on the rear ledge; standard library only, dimensions in mm.

Measured from ESP-Mosaico_Module_Interaction_square4-3D.3mf.
The source shell is not copied or modified. This does not slice or print.
"""
import argparse
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

CAVITY_WIDTH = 9.55
CAVITY_LENGTH = 10.15
END_RADIUS = 0.95
ARC_SEGMENTS = 28
CORE = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'


def outline(width, length, radius, rounded_end=True, inset=0):
    """CCW outline; four rounded corners with fixed centres when inset."""
    r = radius - inset
    centres = [(width-radius, radius, -90),
               (width-radius, length-radius, 0),
               (radius, length-radius, 90),
               (radius, radius, 180)]
    pts = []
    for cx, cy, start in centres:
        for i in range(ARC_SEGMENTS + 1):
            angle = math.radians(start + 90*i/ARC_SEGMENTS)
            pts.append((cx + r*math.cos(angle), cy + r*math.sin(angle)))
    return pts


def plate(width, length, radius, rounded_end, thickness, chamfer):
    outer = outline(width, length, radius, rounded_end)
    foot = outline(width, length, radius, rounded_end, chamfer)
    n = len(outer)
    vertices = [(x, y, 0) for x, y in foot]
    vertices += [(x, y, chamfer) for x, y in outer]
    vertices += [(x, y, thickness) for x, y in outer]
    vertices += [(width / 2, length / 2, 0), (width / 2, length / 2, thickness)]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces += [(3*n, j, i), (3*n+1, 2*n+i, 2*n+j)]
        for k in range(2):
            faces += [(k*n+i, k*n+j, (k+1)*n+j), (k*n+i, (k+1)*n+j, (k+1)*n+i)]
    return vertices, faces


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
    el(root, 'metadata', name='Title').text = 'ESP-Mosaico square4 V2 rear-ledge thin diffuser plates'
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clearance', type=float, default=0.15, help='Gap on EACH side in mm')
    parser.add_argument('--thickness', type=float, default=0.40)
    parser.add_argument('--chamfer', type=float, default=0.05, help='45 degree underside edge chamfer in mm')
    parser.add_argument('--out', type=Path, default=Path(__file__).parent/'print-files')
    args = parser.parse_args()
    if not (0 < args.clearance < 0.6 and 0 < args.chamfer < args.thickness <= 0.6 and args.clearance+args.chamfer < END_RADIUS):
        parser.error('Require 0 < gap < 0.6, 0 < chamfer < thickness <= 0.6, gap + chamfer < 0.95')
    args.out.mkdir(parents=True, exist_ok=True)
    parts = []
    dimensions = []
    for idx in range(4):
        end = True
        width = CAVITY_WIDTH - 2*args.clearance
        length = CAVITY_LENGTH - 2*args.clearance
        radius = END_RADIUS-args.clearance if end else 0
        name = f'{idx+1:02d}_square4_v2_ledge_diffuser'
        vertices, faces = plate(width, length, radius, end, args.thickness, args.chamfer)
        stl(args.out/(name+'.stl'), vertices, faces)
        parts.append((name, vertices, faces))
        dimensions.append(dict(name=name, width_mm=width, length_mm=length,
                               thickness_mm=args.thickness, outer_corner_radius_mm=radius,
                               overlap_past_front_opening_x_mm=(width-8.05)/2,
                               overlap_past_front_opening_y_mm=(length-8.15)/2))
    three_mf(args.out/'mosaico_square4_v2_ledge_040mm_4pcs.3mf', parts)
    (args.out/'dimensions.json').write_text(json.dumps(dict(clearance_per_side_mm=args.clearance,
        bottom_chamfer_mm=args.chamfer, parts=dimensions), indent=2)+'\n')
    print('Generated 4 STL plates and a 4-object 3MF:', args.out)


if __name__ == '__main__':
    main()
