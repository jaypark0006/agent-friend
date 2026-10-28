#!/usr/bin/env python3
"""Partition a square4 integrated front into a shell and four keyed PLA diffuser parts.

Only generates CAD meshes and metadata; does not start a slicer or printer.
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

CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
SOURCE_SHA256='8ee0478b84d0025c83cbcb69b60c0c7910d99190452fc00aada208974aa509da'
X=-16.8875
YS=[16.88247,5.62749,-5.62749,-16.88247]
PARENT=20


def mesh_xml(package,member):
    root=ET.fromstring(package.read(member))
    v=np.array([[float(p.get(k)) for k in ('x','y','z')] for p in root.findall('.//{*}vertex')])
    f=np.array([[int(p.get(k)) for k in ('v1','v2','v3')] for p in root.findall('.//{*}triangle')],dtype=np.uint32)
    return v,f


def rectangle(cx,cy,w,h,r):
    p=[]
    for x,y,start in [(cx+w/2-r,cy-h/2+r,-90),(cx+w/2-r,cy+h/2-r,0),
                      (cx-w/2+r,cy+h/2-r,90),(cx-w/2+r,cy-h/2+r,180)]:
        for i in range(29):
            a=math.radians(start+90*i/28);p.append((x+r*math.cos(a),y+r*math.sin(a)))
    return m.CrossSection([p])


def extrude(shape,z,height):
    return m.Manifold.extrude(shape,height).translate([0,0,z])


def add(parts):
    return m.Manifold.batch_boolean(parts,m.OpType.Add)


def intersect(a,b):
    return m.Manifold.batch_boolean([a,b],m.OpType.Intersect)


def arrays(solid):
    if solid.status()!=m.Error.NoError:raise RuntimeError(f'Mesh construction failed: {solid.status()}')
    data=solid.to_mesh();v=np.array(data.vert_properties[:,:3],dtype=np.float64)
    # Snap shared horizontal material interfaces to the intended 0.20-mm layers.
    for z in (0.,.2,.4,.6,.8):
        v[np.abs(v[:,2]-z)<1e-6,2]=z
    return v,np.array(data.tri_verts,dtype=np.uint32)


def stl(path,v,f):
    with path.open('wb') as stream:
        stream.write(b'Square4 multi-part PLA co-print; shared origin; mm'.ljust(80,b'\0'))
        stream.write(struct.pack('<I',len(f)))
        for ids in f:
            a,b,c=v[ids];n=np.cross(b-a,c-a);mag=np.linalg.norm(n)
            if mag:n/=mag
            stream.write(struct.pack('<12fH',*n,*a,*b,*c,0))


def three_mf(path,parts):
    ET.register_namespace('',CORE)
    def sub(parent,tag,**attrs):
        return ET.SubElement(parent,'{'+CORE+'}'+tag,{k:str(v) for k,v in attrs.items()})
    root=ET.Element('{'+CORE+'}model',unit='millimeter')
    sub(root,'metadata',name='Title').text='Square4 front, 1 shell + 4 keyed PLA diffuser parts'
    sub(root,'metadata',name='Application').text='Codex mesh authoring'
    sub(root,'metadata',name='BambuStudio:3mfVersion').text='1'
    sub(root,'metadata',name='Description').text='One assembly, five separately selectable material parts. Material 1: shell PLA. Material 2: translucent/diffuser PLA. Front face down; keep common coordinates. No printer profiles or G-code.'
    res=sub(root,'resources');mats=sub(res,'basematerials',id=1)
    sub(mats,'base',name='Material_1_Shell_PLA',displaycolor='#E3E6EAFF')
    sub(mats,'base',name='Material_2_Diffuser_PLA',displaycolor='#9ADCECFF')
    ids=[]
    for i,(name,v,f,material) in enumerate(parts,2):
        ids.append(i)
        ob=sub(res,'object',id=i,type='model',name=name,pid=1,pindex=material-1)
        mesh=sub(ob,'mesh');vs=sub(mesh,'vertices');fs=sub(mesh,'triangles')
        for x,y,z in v:sub(vs,'vertex',x=f'{x:.9g}',y=f'{y:.9g}',z=f'{z:.9g}')
        for a,b,c in f:sub(fs,'triangle',v1=int(a),v2=int(b),v3=int(c))
    assembly=sub(res,'object',id=PARENT,type='model',name='Square4_front_multi_material_assembly')
    components=sub(assembly,'components')
    for i in ids:sub(components,'component',objectid=i,transform='1 0 0 0 1 0 0 0 1 0 0 0')
    build=sub(root,'build');sub(build,'item',objectid=PARENT,transform='1 0 0 0 1 0 0 0 1 60 60 0')
    # Mirror the object/part schema from the user's Bambu-authored source file.
    cfg=ET.Element('config');ob=ET.SubElement(cfg,'object',id=str(PARENT))
    ET.SubElement(ob,'metadata',key='name',value='Square4_front_multi_material_assembly')
    ET.SubElement(ob,'metadata',key='extruder',value='1')
    ET.SubElement(ob,'metadata',face_count=str(sum(len(p[2]) for p in parts)))
    for i,(name,v,f,material) in zip(ids,parts):
        part=ET.SubElement(ob,'part',id=str(i),subtype='normal_part')
        ET.SubElement(part,'metadata',key='name',value=name)
        ET.SubElement(part,'metadata',key='extruder',value=str(material))
        ET.SubElement(part,'metadata',key='matrix',value='1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1')
        ET.SubElement(part,'mesh_stat',face_count=str(len(f)),edges_fixed='0',degenerate_facets='0',facets_removed='0',facets_reversed='0',backwards_edges='0')
    plate=ET.SubElement(cfg,'plate')
    ET.SubElement(plate,'metadata',key='plater_id',value='1')
    ET.SubElement(plate,'metadata',key='plater_name',value='Square4 PLA shell and diffuser co-print')
    ET.SubElement(plate,'metadata',key='locked',value='false')
    instance=ET.SubElement(plate,'model_instance')
    for k,val in [('object_id',PARENT),('instance_id',0),('identify_id',1)]:
        ET.SubElement(instance,'metadata',key=k,value=str(val))
    types='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
    rels='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',types);z.writestr('_rels/.rels',rels)
        z.writestr('3D/3dmodel.model',ET.tostring(root,encoding='utf-8',xml_declaration=True))
        z.writestr('Metadata/model_settings.config',ET.tostring(cfg,encoding='utf-8',xml_declaration=True))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path.home()/'Downloads/ESP-Mosaico_Module_Interaction_square4-3D.3mf')
    p.add_argument('--out',type=Path,default=Path(__file__).parent/'print-files')
    a=p.parse_args();sha=hashlib.sha256(a.source.read_bytes()).hexdigest()
    if sha!=SOURCE_SHA256:p.error('Source does not match the measured square4 shell.')
    with zipfile.ZipFile(a.source) as package:v,f=mesh_xml(package,'3D/Objects/object_5.model')
    source_z=float(v[:,2].min());v[:,2]-=source_z
    shell=m.Manifold(m.Mesh(np.asarray(v,dtype=np.float32),f))
    if shell.status()!=m.Error.NoError:raise RuntimeError(f'Source mesh not accepted: {shell.status()}')
    # Preserve the previously delivered integrated outer shape. The change is
    # its material partition, not a new bulge into the electronics cavity.
    envelope=add([shell,*[extrude(rectangle(X,y,9.75,9.85,1.80),0,.4) for y in YS]])
    lenses=[]
    for y in YS:
        face=rectangle(X,y,9.25,9.35,1.55)
        neck=rectangle(X,y,9.75,9.85,1.80)
        head=rectangle(X,y,10.55,10.15,1.95)
        clear_hole=rectangle(X,y,8.05,8.15,.95)
        keyed=add([extrude(face,0,.2),extrude(head,.2,.2),
                   extrude(neck-clear_hole,.4,.2),extrude(head-clear_hole,.6,.2)])
        # Restrict keys to existing envelope; preserve every original cavity.
        lenses.append(intersect(keyed,envelope))
    opaque=envelope-add(lenses)
    parts=[]
    for i,solid in enumerate([opaque,*lenses]):
        if solid.status()!=m.Error.NoError:raise RuntimeError(f'Part {i} construction failed: {solid.status()}')
        name='00_shell_PLA_material_1' if i==0 else f'{i:02d}_diffuser_PLA_material_2'
        verts,faces=arrays(solid);parts.append((name,verts,faces,1 if i==0 else 2))
    a.out.mkdir(parents=True,exist_ok=True)
    for name,verts,faces,material in parts:stl(a.out/(name+'.stl'),verts,faces)
    three_mf(a.out/'square4_front_PLA_2materials_5parts.3mf',parts)
    info=dict(source_file=a.source.name,source_sha256=sha,source_front_z_mm=source_z,
        revision='Two-PLA multipart co-print, 2026-10-19',assembly_count=1,material_part_count=5,
        membrane_thickness_mm=.4,peripheral_key_height_mm=.8,
        nominal_layer_height_mm=.2,body_material=1,diffuser_material=2,
        layer_interfaces=[{'z_mm':[0,.2],'shape':'Front visible membrane, 9.25 x 9.35 R1.55'},
            {'z_mm':[.2,.4],'shape':'Full wider shoulder, 10.55 x 10.15 R1.95; clipped to original envelope'},
            {'z_mm':[.4,.6],'shape':'Narrower peripheral neck, 9.75 x 9.85 R1.80; centre stays hollow'},
            {'z_mm':[.6,.8],'shape':'Wider peripheral head; centre stays hollow'},
            {'z_mm':[.8,1.2],'shape':'Original shell covers outer head; optical aperture unchanged'}],
        x_shoulder_step_mm=.4,y_shoulder_step_mm=.15,
        material_partition='Each lens is intersected with the original integrated envelope; shell = envelope minus all four lenses.',
        joint_clearance_mm=0,import_as='One assembly, five material parts, shared coordinates; print together.',
        parts=[{'name':n,'material':mat,'mesh_build_status':str(solid.status()),
                'volume_mm3':solid.volume()} for (n,_,_,mat),solid in zip(parts,[opaque,*lenses])],
        slicer_run=False,print_run=False,interface_strength_verified=False,optical_performance_verified=False)
    (a.out/'model-information.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    # Actual mesh cross sections for the technical drawing, not a slicer output.
    sections=[]
    clip=m.CrossSection.square([11.5,1.3]).translate([X-5.75,-1.3])
    for solid,label in [(opaque,'Shell PLA'),(lenses[1],'Diffuser PLA')]:
        polygons=(solid.rotate([90,0,0]).slice(YS[1]) ^ clip).to_polygons()
        sections.append({'material':label,'polygons_x_negz':[np.asarray(q).tolist() for q in polygons]})
    (a.out/'interface-section.json').write_text(json.dumps(sections,indent=2)+'\n')
    print(json.dumps({'generated':str(a.out),'material_parts':5,'centre_thickness_mm':.4,
        'key_height_mm':.8,'part_statuses':[str(o.status()) for o in [opaque,*lenses]]}))


if __name__=='__main__':main()
