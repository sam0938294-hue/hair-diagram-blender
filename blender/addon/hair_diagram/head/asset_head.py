"""CC0 MakeHuman hm08 head/neck, with source topology retained."""
from pathlib import Path
import bpy
import bmesh
from ..core import collections, materials

SOURCE = Path(__file__).resolve().parents[1] / 'assets/vendor/makehuman/base.obj'

def create(source=None):
    source = Path(source or SOURCE)
    vertices, faces, group = [], [], ''
    for line in source.read_text(encoding='utf-8').splitlines():
        if line.startswith('v '):
            x,y,z = map(float,line.split()[1:4])
            vertices.append((x*.095, -(z-.55)*.095, (y-7.4)*.095))
        elif line.startswith('g '): group = line[2:].strip()
        elif line.startswith('f ') and group == 'body':
            face = [int(v.split('/')[0])-1 for v in line.split()[1:]]
            if max(vertices[i][2] for i in face) > -.137:
                faces.append(face)
    used = sorted({i for f in faces for i in f})
    mapping = {v:i for i,v in enumerate(used)}
    data = bpy.data.meshes.new('MakeHuman_CC0_HeadTopology')
    data.from_pydata([vertices[i] for i in used], [], [[mapping[i] for i in f] for f in faces])
    bm = bmesh.new(); bm.from_mesh(data)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
        dist=1e-6, plane_co=(0,0,-.137), plane_no=(0,0,1), clear_inner=True)
    rim = [e for e in bm.edges if e.is_boundary and all(abs(v.co.z+.137)<1e-5 for v in e.verts)]
    if rim:
        bmesh.ops.holes_fill(bm, edges=rim, sides=0)
        crease=bm.edges.layers.float.new('crease_edge')
        for e in bm.edges:
            if all(abs(v.co.z+.137)<1e-5 for v in e.verts):e[crease]=1.0
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data); bm.free()
    obj = bpy.data.objects.new('HD_HEAD_BASE', data)
    collections.link(obj, 'HEAD')
    materials.assign(obj, materials.ensure_surface('PORCELAIN',(.66,.67,.68,1)))
    for p in data.polygons:
        p.use_smooth=not all(abs(data.vertices[i].co.z+.137)<1e-5 for i in p.vertices)
    mod=obj.modifiers.new('Editable subdivision','SUBSURF'); mod.levels=2; mod.render_levels=2
    obj['source']='MakeHuman Community / hm08 base.obj / CC0 (2020)'
    obj['source_url']='https://github.com/makehumancommunity/makehuman/blob/master/makehuman/data/3dobjs/base.obj'
    obj['dimensions_note']='Uniformly scaled to adult mannequin size; not a measured individual.'
    # Solid untextured eyeballs behind the original eyelids.
    for side in [-1,1]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,radius=.0128,
            location=(side*.30775*.095,-(1.241-.55)*.095,(7.284-7.4)*.095))
        eye=bpy.context.object; eye.name='HD_EYE_'+str(side)
        collections.link(eye,'HEAD'); materials.assign(eye,materials.ensure_surface('PORCELAIN',(.66,.67,.68,1)))
        for p in eye.data.polygons:p.use_smooth=True
    bpy.context.view_layer.update()
    return obj
