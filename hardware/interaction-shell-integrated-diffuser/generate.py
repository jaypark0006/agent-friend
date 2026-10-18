#!/usr/bin/env python3
"""Fuse four bed-supported 0.40-mm diffuser windows into the original square4 front shell.

This builds mesh assets only: no slicer, printer or device validation is run.
Dependencies: numpy and manifold3d, see requirements-modeling.txt.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import manifold3d as m

SOURCE_SHA256='8ee0478b84d0025c83cbcb69b60c0c7910d99190452fc00aada208974aa509da'
FRONT_PATH='3D/Objects/object_5.model'
BACK_PATH='3D/Objects/object_6.model'
CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
FILM_CENTRES_Y=[16.88247,5.62749,-5.62749,-16.88247]
FILM_CENTRE_X=-16.8875
FILM_WIDTH=9.75
FILM_LENGTH=9.85
FILM_RADIUS=1.80


def mesh_from_xml(package, path):
    root=ET.fromstring(package.read(path))
    vertices=np.array([[float(p.get(k)) for k in ('x','y','z')]
                       for p in root.findall('.//{*}vertex')],dtype=np.float64)
    faces=np.array([[int(p.get(k)) for k in ('v1','v2','v3')]
                    for p in root.findall('.//{*}triangle')],dtype=np.uint32)
    return vertices,faces


def rounded_rectangle(cx,cy,width,length,radius):
    pts=[]
    centres=[(cx+width/2-radius,cy-length/2+radius,-90),
             (cx+width/2-radius,cy+length/2-radius,0),
             (cx-width/2+radius,cy+length/2-radius,90),
             (cx-width/2+radius,cy-length/2+radius,180)]
    for x,y,start in centres:
        for i in range(29):
            a=math.radians(start+90*i/28)
            pts.append((x+radius*math.cos(a),y+radius*math.sin(a)))
    return pts


def export_stl(path,vertices,faces):
    with path.open('wb') as stream:
        stream.write(b'Square4 front shell with integrated diffuser; mm; front face on bed'.ljust(80,b'\0'))
        stream.write(struct.pack('<I',len(faces)))
        for ids in faces:
            a,b,c=vertices[ids]
            n=np.cross(b-a,c-a)
            mag=np.linalg.norm(n)
            if mag: n=n/mag
            stream.write(struct.pack('<12fH',*n,*a,*b,*c,0))


def export_3mf(path,objects,title):
    ET.register_namespace('',CORE)
    def sub(parent,tag,**kw):
        return ET.SubElement(parent,'{'+CORE+'}'+tag,{k:str(v) for k,v in kw.items()})
    model=ET.Element('{'+CORE+'}model',unit='millimeter')
    sub(model,'metadata',name='Title').text=title
    sub(model,'metadata',name='Description').text='Front face down. White PLA. Integrated 0.40 mm window films start on the bed; no separate inserts. No printer profile or G-code included.'
    resources=sub(model,'resources')
    mats=sub(resources,'basematerials',id=1)
    sub(mats,'base',name='White PLA',displaycolor='#FFFFFFFF')
    build=sub(model,'build')
    for i,(name,vertices,faces,x,y) in enumerate(objects,2):
        obj=sub(resources,'object',id=i,type='model',name=name,pid=1,pindex=0)
        mesh=sub(obj,'mesh');vs=sub(mesh,'vertices');fs=sub(mesh,'triangles')
        for a,b,c in vertices:sub(vs,'vertex',x=f'{a:.9g}',y=f'{b:.9g}',z=f'{c:.9g}')
        for a,b,c in faces:sub(fs,'triangle',v1=int(a),v2=int(b),v3=int(c))
        sub(build,'item',objectid=i,transform=f'1 0 0 0 1 0 0 0 1 {x} {y} 0')
    types='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
    rels='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as package:
        package.writestr('[Content_Types].xml',types)
        package.writestr('_rels/.rels',rels)
        package.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path.home()/'Downloads/ESP-Mosaico_Module_Interaction_square4-3D.3mf')
    parser.add_argument('--out',type=Path,default=Path(__file__).parent/'print-files')
    parser.add_argument('--thickness',type=float,default=0.40)
    args=parser.parse_args()
    digest=hashlib.sha256(args.source.read_bytes()).hexdigest()
    if digest!=SOURCE_SHA256:parser.error('Source differs from measured square4 file; do not silently apply these film positions.')
    if not 0.2<=args.thickness<=0.6:parser.error('Require film thickness between 0.20 and 0.60 mm.')
    with zipfile.ZipFile(args.source) as package:
        original,triangles=mesh_from_xml(package,FRONT_PATH)
        back,back_faces=mesh_from_xml(package,BACK_PATH)
    front_z=float(original[:,2].min())
    raw=m.Mesh(np.asarray(original,dtype=np.float32),triangles)
    shell=m.Manifold(raw)
    # Import must be accepted before any output is authored; no mesh repair or
    # recreation of unrelated shell features is performed by this generator.
    if shell.status()!=m.Error.NoError:
        raise RuntimeError(f'Cannot build original source shell: {shell.status()}')
    films=[]
    for y in FILM_CENTRES_Y:
        contour=rounded_rectangle(FILM_CENTRE_X,y,FILM_WIDTH,FILM_LENGTH,FILM_RADIUS)
        films.append(m.Manifold.extrude(m.CrossSection([contour]),args.thickness).translate([0,0,front_z]))
    joined=m.Manifold.batch_boolean([shell,*films],m.OpType.Add)
    if joined.status()!=m.Error.NoError:
        raise RuntimeError(f'Cannot build shell/film union: {joined.status()}')
    result=joined.to_mesh()
    vertices=np.array(result.vert_properties[:,:3],dtype=np.float64)
    faces=np.array(result.tri_verts,dtype=np.uint32)
    # Original source build uses front_z + 5.44999981 = 0. Preserve that
    # face-down direction, explicitly placing the new front mesh at Z=0.
    vertices[:,2]-=front_z
    vertices[np.abs(vertices[:,2])<1e-7,2]=0.0
    vertices[np.abs(vertices[:,2]-args.thickness)<1e-7,2]=args.thickness
    back=back.copy();back[:,2]-=float(back[:,2].min())
    args.out.mkdir(parents=True,exist_ok=True)
    tag=f'{round(args.thickness*100):03d}mm'
    name=f'square4_front_integrated_diffuser_{tag}'
    export_stl(args.out/(name+'.stl'),vertices,faces)
    front_obj=('Modified_front_shell_with_integrated_diffuser',vertices,faces,60,60)
    back_obj=('Original_back_cover_geometry',back,back_faces,60,112)
    export_3mf(args.out/(name+'.3mf'),[front_obj],name)
    export_3mf(args.out/f'square4_complete_integrated_diffuser_{tag}.3mf',[front_obj,back_obj],
               'Square4 modified front + original back cover, face-down print arrangement')
    data=dict(source_file=args.source.name,source_sha256=digest,front_source=FRONT_PATH,
        back_source=BACK_PATH,revision='Integrated shell, 2026-10-19',
        source_front_face_z_mm=front_z,film_thickness_mm=args.thickness,
        film_centres_source_xy=[[FILM_CENTRE_X,y] for y in FILM_CENTRES_Y],
        patch_width_mm=FILM_WIDTH,patch_length_mm=FILM_LENGTH,patch_radius_mm=FILM_RADIUS,
        construction='Boolean union with original front shell; patches overlap original front rim.',
        print_orientation='Original front face down; new thin films begin at build-plane Z=0.',
        source_shell_bounds_mm=[original.min(0).tolist(),original.max(0).tolist()],
        result_print_bounds_mm=[vertices.min(0).tolist(),vertices.max(0).tolist()],
        build_status=str(joined.status()),source_volume_mm3=shell.volume(),result_volume_mm3=joined.volume(),
        front_exported_as_one_object=True,back_cover_geometry_modified=False,
        slicer_run=False,physical_fit_verified=False,optical_performance_verified=False)
    (args.out/'model-information.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(generated=str(args.out),build_status=str(joined.status()),
        front_faces=len(faces),added_volume_mm3=joined.volume()-shell.volume(),
        film_thickness_mm=args.thickness),ensure_ascii=False))


if __name__=='__main__':main()
