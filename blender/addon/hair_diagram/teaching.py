"""Editable scalp diagrams. Styling parameters are explicit, not inferred haircuts."""
import math
import json
import bpy
from mathutils import Vector
from . import config
from .core import materials, surface

def collection(name):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c

def mesh(name,verts,faces,mat,group):
    data=bpy.data.meshes.new(name); data.from_pydata(verts,[],faces); data.update()
    o=bpy.data.objects.new(name,data); collection(group).objects.link(o); data.materials.append(mat)
    for p in data.polygons:p.use_smooth=True
    return o

def line(name,points,mat,group='HD_TEACH_SECTIONS',radius=.00035):
    data=bpy.data.curves.new(name,'CURVE'); data.dimensions='3D';data.bevel_depth=radius;data.bevel_resolution=3
    s=data.splines.new('POLY');s.points.add(len(points)-1)
    for p,co in zip(s.points,points):p.co=(*co,1)
    o=bpy.data.objects.new(name,data);collection(group).objects.link(o);data.materials.append(mat)
    return o

def _meridian_points(front_az, back_az, steps=64):
    """One continuous scalp curve from a hairline edge, over the apex, to the opposite edge."""
    front_lo=boundary(front_az);back_lo=boundary(back_az)
    front=[point(front_az,front_lo+(89.75-front_lo)*i/steps)[0] for i in range(steps+1)]
    back=[point(back_az,89.75-(89.75-back_lo)*i/steps)[0] for i in range(1,steps+1)]
    return front+back

def _ring_points(elevation,start=0,end=360,steps=180):
    return [point(start+(end-start)*i/steps,elevation)[0] for i in range(steps+1)]

def _rear_arc_points(elevation,start=122,end=238,steps=72):
    result=[]
    for i in range(steps+1):
        az=start+(end-start)*i/steps
        if elevation>=boundary(az):result.append(point(az,elevation)[0])
    return result

def _ear_to_bp_points(side,steps=90):
    """Join the ear meridian's hairline endpoint to the lowered rear junction."""
    result=[]
    for i in range(steps+1):
        t=i/steps;az=side*(90+90*t)
        # Ease the elevation into B.P. so the two sides meet without a kink.
        blend=t*t*(3-2*t)
        el=boundary(90)+(config.REFERENCE_BP_ELEVATION-boundary(90))*blend
        result.append(point(az,el)[0])
    return result

def reference_network(mat):
    """Sparse, label-free teaching construction lines based on the supplied reference image."""
    made=[]
    made.append(line('HD_REF_CENTER_FRONT_BACK',_meridian_points(0,180),mat,radius=.00043))
    made.append(line('HD_REF_EAR_TO_EAR',_meridian_points(90,270),mat,radius=.00040))
    made.append(line('HD_REF_UPPER_CROWN',_ring_points(58),mat,radius=.00038))
    # Replace the crossed-out belt with the two arrow endpoints' connection.
    made.append(line('HD_REF_LEFT_EP_BP',_ear_to_bp_points(1),mat,radius=.00043))
    made.append(line('HD_REF_RIGHT_EP_BP',_ear_to_bp_points(-1),mat,radius=.00043))
    made.append(line('HD_REF_OCCIPITAL',_rear_arc_points(-10),mat,radius=.00038))
    for obj in made:
        obj['hd_reference']='locked initial construction line'
        obj['reference_note']='Approximate editable-system background based on user-supplied diagram; no universal landmark claim.'
    return made

def lock_reference_objects():
    """Keep the mannequin and its background guides visible but impossible to select."""
    names=('HD_HEAD','HD_TEACH_SCALP','HD_TEACH_HAIRLINE','HD_TEACH_SECTIONS')
    locked=[]
    for name in names:
        c=bpy.data.collections.get(name)
        if not c:continue
        c.hide_select=True
        for obj in c.all_objects:
            if obj is None:continue
            obj.hide_select=True
            try:obj.select_set(False)
            except RuntimeError:pass
            obj['hd_locked_reference']=True
            locked.append(obj)
    active=bpy.context.view_layer.objects.active
    if active and active in locked:bpy.context.view_layer.objects.active=None
    return locked

def boundary(az):
    # An editable, designed mannequin hairline; not anatomical measurement.
    a=abs((az+180)%360-180)
    knots=[(0,29),(25,30),(45,24),(65,6),(78,14),(95,14),(113,-9),(135,-29),(160,-40),(180,-42)]
    for (x,y),(xx,yy) in zip(knots,knots[1:]):
        if x<=a<=xx:
            t=(a-x)/(xx-x);t=t*t*(3-2*t)
            return y+(yy-y)*t
    return -42

def point(az,el,offset=.00065):
    return surface.project(surface.spherical_direction(az,el),offset=offset)

def scalp():
    black=materials.ensure_ink('TEACH_INK',(.055,.063,.073,1))
    gray=materials.ensure_ink('TEACH_GRID',(.30,.34,.37,1))
    cap=materials.ensure_surface('SCALP',(.48,.51,.53,1))
    verts=[]; faces=[]; nu=144;nv=28
    for j in range(nv+1):
        for i in range(nu):
            az=i*360/nu;lo=boundary(az)
            verts.append(point(az,lo+(89.9-lo)*j/nv, .0004)[0])
    for j in range(nv):
        for i in range(nu):
            a=j*nu+i;b=j*nu+(i+1)%nu
            faces.append((a,b,b+nu,a+nu))
    pole=len(verts)
    verts.append(point(0,90,.0004)[0])
    for i in range(nu):faces.append((nv*nu+i,nv*nu+(i+1)%nu,pole))
    mesh('HD_SCALP_SURFACE',verts,faces,cap,'HD_TEACH_SCALP')
    line('HD_HAIRLINE',[point(i*360/288,boundary(i*360/288))[0] for i in range(289)],black,'HD_TEACH_HAIRLINE',.00055)
    reference_network(black)
    lock_reference_objects()
    bpy.context.scene['hairline_note']='Designed symmetric hairline; edit boundary() for client-specific outlines.'

def clear_panels():
    c=bpy.data.collections.get('HD_TEACH_PANELS')
    if c:
        for o in list(c.objects):
            d=o.data;bpy.data.objects.remove(o,do_unlink=True)
            if d.users==0:
                if isinstance(d,bpy.types.Mesh):bpy.data.meshes.remove(d)
                elif isinstance(d,bpy.types.Curve):bpy.data.curves.remove(d)

def panels(mode='NORMAL',length_cm=7.0,elevation=90.0):
    clear_panels()
    if mode=='BASE':return
    coral=materials.ensure_ink('CUT',(.78,.105,.19,1))
    black=materials.ensure_ink('STRAND',(.10,.13,.16,1))
    pink=materials.ensure_translucent('PANEL',(.90,.22,.32,.14))
    group='HD_TEACH_PANELS';length=length_cm/100
    for panel,az in enumerate([55,85,115,145]):
        roots=[]; tips=[]
        for j in range(9):
            el=20+j*6.5
            r,n=point(az,el,.0009)
            if mode=='UP':d=Vector((0,0,1))
            else:
                down=Vector((0,0,-1));t=down-n*down.dot(n)
                if t.length<1e-6:t=Vector((0,-1,0))
                t.normalize();a=math.radians(elevation)
                d=t*math.cos(a)+n*math.sin(a)
            end=r+d*length
            roots.append(r);tips.append(end)
            o=line('HD_STRAND_%d_%d'%(panel,j),[r,end],black,group,.00024)
            o['root']=list(r);o['normal']=list(n);o['length_cm']=length_cm
            o['reference']='world +Z' if mode=='UP' else 'local downward scalp tangent; 90 = surface normal'
        vs=roots+tips;n=len(roots)
        faces=[(i,i+1,n+i+1,n+i) for i in range(n-1)]
        o=mesh('HD_HAIR_PANEL_%d'%panel,vs,faces,pink,group)
        o['recipe']=json.dumps(dict(azimuth=az,mode=mode,length_cm=length_cm,elevation=elevation))
        line('HD_CUT_EDGE_%d'%panel,tips,coral,group,.00052)
        line('HD_ROOT_EDGE_%d'%panel,roots,coral,group,.00043)
        for j in [0,-1]:line('HD_PANEL_EDGE_%d_%d'%(panel,j),[roots[j],tips[j]],coral,group,.00032)
    bpy.context.scene['teaching_recipe']=json.dumps(dict(mode=mode,length_cm=length_cm,elevation=elevation))

class HDTeachingSettings(bpy.types.PropertyGroup):
    mode:bpy.props.EnumProperty(name='Diagram',items=[('BASE','Base / 分區底圖',''),('NORMAL','Local elevation / 頭皮提拉',''),('UP','Upward distribution / 向上分配','')],default='NORMAL')
    length:bpy.props.FloatProperty(name='Length (cm)',default=7,min=1,max=15)
    elevation:bpy.props.FloatProperty(name='Local elevation',default=90,min=0,max=90)
    camera:bpy.props.EnumProperty(name='View',items=[(k,k.replace('_',' ').title(),'') for k in ['front','front_left_45','left','back_left_45','back','right','top']],default='front_left_45')

class HD_OT_teaching_update(bpy.types.Operator):
    bl_idname='hd.teaching_update';bl_label='Update diagram / 更新圖示';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        if not bpy.data.objects.get('HD_HEAD_BASE'):
            self.report({'ERROR'},'Open teaching_head.blend first');return {'CANCELLED'}
        s=context.scene.hd_teaching;panels(s.mode,s.length,s.elevation)
        from .view import cameras
        cameras.set_active(s.camera)
        for a in context.screen.areas:
            if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA'
        return {'FINISHED'}

class HD_PT_teaching(bpy.types.Panel):
    bl_label='Hair Diagram / 美髮教材';bl_idname='HD_PT_teaching';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Hair Diagram'
    @classmethod
    def poll(cls,context):
        return not context.scene.get('hd_editor_version')
    def draw(self,context):
        l=self.layout;s=context.scene.hd_teaching
        l.prop(s,'mode');l.prop(s,'length')
        if s.mode=='NORMAL':
            l.prop(s,'elevation');l.label(text='90 = scalp normal / 頭皮法線')
        elif s.mode=='UP':l.label(text='World +Z / 固定向上，非局部90度')
        l.prop(s,'camera');l.operator('hd.teaching_update')
        l.label(text='F12: Render | Outliner: Toggle layers')
        l.label(text='低角度為直線幾何，非自然垂落模擬')

CLASSES=(HDTeachingSettings,HD_OT_teaching_update,HD_PT_teaching)
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.hd_teaching=bpy.props.PointerProperty(type=HDTeachingSettings)
def unregister():
    del bpy.types.Scene.hd_teaching
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
