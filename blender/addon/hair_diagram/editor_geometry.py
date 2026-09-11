"""Geometry for the v0.3 scalp editor. No UI context is required.
All lengths are SI internally; stored user parameters use cm / mm / degrees.
"""
import math
import hashlib
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
from .core import materials

OFFSET = .0009

def world_bvh(obj,smooth=False):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data = evaluated.to_mesh()
    try:
        verts = [evaluated.matrix_world @ v.co for v in data.vertices]
        if smooth:
            data.calc_loop_triangles()
            faces=[tuple(t.vertices) for t in data.loop_triangles]
            normal_matrix=evaluated.matrix_world.to_3x3().inverted().transposed()
            normals=[(normal_matrix@v.normal).normalized() for v in data.vertices]
            return BVHTree.FromPolygons(verts,faces,all_triangles=True),verts,normals,faces
        faces = [tuple(p.vertices) for p in data.polygons]
        return BVHTree.FromPolygons(verts, faces, all_triangles=False)
    finally:
        evaluated.to_mesh_clear()

class Scalp:
    def __init__(self):
        obj = bpy.data.objects.get('HD_SCALP_SURFACE')
        if obj is None:
            raise ValueError('請先開啟自由編輯頭模。')
        self.tree = world_bvh(obj)
        head = bpy.data.objects.get('HD_HEAD_BASE')
        self.head_tree=None
        if head:
            self.head_tree,self.head_verts,self.head_normals,self.head_tris=world_bvh(head,smooth=True)
        self.center = head.matrix_world.translation.copy() if head else Vector((0,0,0))

    def normal_at(self,p,fallback):
        n=fallback
        if self.head_tree:
            hp,head_n,tri,dist=self.head_tree.find_nearest(p)
            if head_n is not None and dist<.004:
                a,b,c=self.head_tris[tri]
                n=barycentric_transform(hp,self.head_verts[a],self.head_verts[b],self.head_verts[c],
                    self.head_normals[a],self.head_normals[b],self.head_normals[c])
        if n.dot(p-self.center)<0:n=-n
        return n.normalized()

    def nearest(self, position):
        p,n,_,_ = self.tree.find_nearest(Vector(position))
        if p is None: raise ValueError('找不到頭皮表面。')
        return p,self.normal_at(p,n)

    def radial(self, position):
        d = Vector(position)-self.center
        if d.length < 1e-8: raise ValueError('請在兩點之間多加一個轉折點。')
        d.normalize()
        p,n,_,_ = self.tree.ray_cast(self.center+d*2,-d,4)
        if p is None or (p-self.center).dot(d)<=0:
            raise ValueError('分線穿過髮際線外，請沿頭皮多點幾個轉折點。')
        return p,self.normal_at(p,n)

    def pick(self, origin, direction):
        p,n,_,dist = self.tree.ray_cast(origin,direction,10)
        if p is None:return None
        # Do not pick the far scalp through the face or ears.
        if self.head_tree:
            _,_,_,head_dist = self.head_tree.ray_cast(origin,direction,10)
            if head_dist is not None and head_dist < dist-.002:return None
        return p,self.normal_at(p,n)

    def path(self, controls, closed=False):
        controls=[self.nearest(p)[0] for p in controls]
        if len(controls)<2: raise ValueError('至少需要兩個不同的點。')
        if closed:controls=controls+[controls[0]]
        result=[]
        for a,b in zip(controls,controls[1:]):
            da=(a-self.center).normalized();db=(b-self.center).normalized()
            if da.dot(db)<-.95:raise ValueError('兩點距離太遠，請補一個中間點。')
            if (b-a).length<.0001:continue
            steps=max(8,math.ceil((b-a).length/.001))
            for j in range(steps):
                u=j/steps
                direction=da.lerp(db,u).normalized()
                p,n=self.radial(self.center+direction*.2)
                result.append(p+n*OFFSET)
        p,n=self.nearest(controls[-1]);result.append(p+n*OFFSET)
        if len(result)<2:raise ValueError('兩點太接近，請重新點選。')
        return result

def resample(points,count):
    lengths=[0.0]
    for a,b in zip(points,points[1:]):lengths.append(lengths[-1]+(b-a).length)
    if lengths[-1]<1e-7:raise ValueError('分線太短。')
    result=[];segment=0
    for i in range(count):
        target=lengths[-1]*i/(count-1)
        while segment<len(points)-2 and lengths[segment+1]<target:segment+=1
        t=(target-lengths[segment])/max(1e-12,lengths[segment+1]-lengths[segment])
        result.append(points[segment].lerp(points[segment+1],t))
    return result

def basis(normal, reference, swivel):
    n=Vector(normal).normalized();down=Vector((0,0,-1))
    if reference=='WORLD':
        az=math.radians(swivel)
        return down,Vector((math.sin(az),-math.cos(az),0))
    t=down-n*down.dot(n)
    if t.length<.03:
        front=Vector((0,-1,0));t=front-n*front.dot(n)
    t.normalize()
    angle=math.radians(swivel)
    t=t*math.cos(angle)+n.cross(t)*math.sin(angle)
    return t.normalized(),n

def direction(t,n,angle):
    a=math.radians(angle)
    return (t*math.cos(a)+n*math.sin(a)).normalized()

def panel_geometry(item,controls,scalp):
    dense=scalp.path(controls)
    roots=[];normals=[]
    for p in resample(dense,item.strands):
        p,n=scalp.nearest(p);roots.append(p+n*OFFSET);normals.append(n)
    mid=len(roots)//2
    ct,cn=basis(normals[mid],item.reference,item.swivel)
    dirs=[]
    for normal in normals:
        t,n=basis(normal,item.reference,item.swivel)
        if item.reference=='CENTER':t,n=ct,cn
        dirs.append(direction(t,n,item.elevation))
    lengths=[item.length_cm/100]*len(roots)
    if item.cut_mode=='TAPER':
        lengths=[(item.length_cm+(item.end_length_cm-item.length_cm)*i/(len(roots)-1))/100 for i in range(len(roots))]
    if item.cut_mode=='PLANE':
        d=dirs[mid]
        q=roots[-1]-roots[0];q=q-d*q.dot(d)
        if q.length<1e-5:raise ValueError('分線與提拉方向太接近，無法定義切口，請換方向。')
        q.normalize();a=math.radians(item.cut_angle)
        plane_n=d*math.sin(a)-q*math.cos(a)
        plane_p=roots[mid]+d*item.length_cm/100
        lengths=[]
        for r,v in zip(roots,dirs):
            denominator=v.dot(plane_n)
            if abs(denominator)<.025:raise ValueError('部分髮束與切口平行，請調整切口或提拉角度。')
            length=(plane_p-r).dot(plane_n)/denominator
            if not .001<length<.6:raise ValueError('切口落在毛根後方或超過60公分，請調整角度或髮長。')
            lengths.append(length)
    tips=[r+d*l for r,d,l in zip(roots,dirs,lengths)]
    return dict(roots=roots,normals=normals,tips=tips,lengths=lengths,basis=(ct,cn),dense=dense)

def erase(objects):
    for obj in list(objects):
        data=obj.data
        bpy.data.objects.remove(obj,do_unlink=True)
        if data and data.users==0:
            if isinstance(data,bpy.types.Mesh):bpy.data.meshes.remove(data)
            elif isinstance(data,bpy.types.Curve):bpy.data.curves.remove(data)

def group():
    c=bpy.data.collections.get('HD_EDITOR_教材元素')
    if c is None:
        c=bpy.data.collections.new('HD_EDITOR_教材元素');bpy.context.scene.collection.children.link(c)
    return c

def color_material(color,alpha=1):
    key=hashlib.sha1(str(tuple(round(x,4) for x in color)+(round(alpha,4),)).encode()).hexdigest()[:12]
    if alpha<1:return materials.ensure_translucent('ED_'+key,(*color[:3],alpha))
    return materials.ensure_ink('ED_'+key,(*color[:3],1))

class Drawing:
    def __init__(self,item):
        self.item=item;self.objects=[]
        self.ink=color_material(item.color);self.edge=color_material(item.edge_color)
        self.radius=item.width_mm/2000

    def attach(self,name,data,mat,role='LINE'):
        obj=bpy.data.objects.new('HD_ED_'+name,data);group().objects.link(obj)
        data.materials.append(mat);obj['hd_editor_id']=self.item.uid;obj['hd_role']=role
        self.objects.append(obj)
        return obj

    def line(self,name,points,mat=None,dashed=False,radius=None):
        data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.bevel_depth=radius or self.radius;data.bevel_resolution=3
        pieces=[]
        if dashed:
            phase=0.0
            for a,b in zip(points,points[1:]):
                length=(b-a).length
                if length<1e-9:continue
                pos=0.0
                while pos<length-1e-9:
                    cycle=phase%.005
                    draw=cycle<.003-1e-8
                    step=min(length-pos,(.003 if draw else .005)-cycle)
                    if step<1e-8:phase+=1e-7;continue
                    if draw:pieces.append([a.lerp(b,pos/length),a.lerp(b,(pos+step)/length)])
                    pos+=step;phase+=step
        else:pieces=[points]
        for piece in pieces:
            if len(piece)<2:continue
            s=data.splines.new('POLY');s.points.add(len(piece)-1)
            for p,v in zip(s.points,piece):p.co=(*v,1)
        return self.attach(name,data,mat or self.ink)

    def dot(self,position):
        bm=bmesh.new();bmesh.ops.create_uvsphere(bm,u_segments=16,v_segments=8,radius=self.item.point_mm/2000)
        data=bpy.data.meshes.new('Point');bm.to_mesh(data);bm.free()
        o=self.attach('Point',data,self.ink,'DOT');o.location=position
        for p in data.polygons:p.use_smooth=True
        return o

    def arrow(self,a,b):
        v=b-a
        if v.length<.0001:return
        length=min(.005,v.length*.25);bm=bmesh.new()
        bmesh.ops.create_cone(bm,cap_ends=True,cap_tris=False,segments=12,radius1=self.radius*3.5,radius2=0,depth=length)
        data=bpy.data.meshes.new('ArrowTip');bm.to_mesh(data);bm.free()
        o=self.attach('ArrowTip',data,self.ink)
        o.location=b-v.normalized()*length*.5;o.rotation_euler=v.to_track_quat('Z','Y').to_euler()

    def text(self,text,position,role='LABEL'):
        from .editor import load_font
        load_font()
        data=bpy.data.curves.new('Label','FONT');data.body=text;data.size=self.item.label_mm/1000;data.align_x='CENTER'
        font=bpy.data.fonts.get('HD_CHINESE')
        if font:data.font=font
        o=self.attach('Label',data,self.ink,role);o.location=position
        c=o.constraints.new('COPY_ROTATION');c.name='HD_BILLBOARD';c.target=bpy.context.scene.camera
        o['hd_billboard']=True
        return o

    def angle(self,root,t,n,value,length):
        r=min(length*.55,.025)
        self.line('ZeroReference',[root,root+t*r],dashed=True)
        arc=[root+direction(t,n,value*j/48)*r for j in range(49)]
        if value>0:self.line('AngleArc',arc,mat=self.edge)
        self.text(f'{value:g}°',root+direction(t,n,value*.5)*(r+.009),'INFO')

    def build(self,controls,scalp):
        i=self.item
        if i.kind=='POINT':
            p,n=scalp.nearest(controls[0]);p+=n*OFFSET
            self.dot(p)
            self.text(i.name,p+n*.008+Vector((i.label_dx/1000,0,i.label_dz/1000)))
        elif i.kind=='SURFACE':
            self.line('ScalpLine',scalp.path(controls,i.closed),dashed=i.dashed)
        elif i.kind=='GUIDE':
            self.line('Guide',controls,dashed=i.dashed)
            if i.arrow:self.arrow(controls[-2],controls[-1])
        elif i.kind in {'RAY','FAN'}:
            p,n=scalp.nearest(controls[0]);p+=n*OFFSET
            t,n=basis(n,i.reference,i.swivel);length=i.length_cm/100
            if i.kind=='RAY':
                end=p+direction(t,n,i.elevation)*length
                self.line('Lift',[p,end],dashed=i.dashed)
                if i.arrow:self.arrow(p,end)
                if i.show_angle:self.angle(p,t,n,i.elevation,length)
                if i.show_length:self.text(f'{i.length_cm:g} cm',end+Vector((0,0,.006)),'INFO')
            else:
                angles=list(range(0,181,30))
                for a in angles:
                    end=p+direction(t,n,a)*length
                    self.line('FanRay',[p,end],dashed=i.dashed)
                    if i.arrow:self.arrow(p,end)
                    self.text(f'{a}°',p+direction(t,n,a)*(length+.008),'INFO')
                self.line('FanArc',[p+direction(t,n,a)*length for a in range(181)],mat=self.edge)
        elif i.kind=='PANEL':
            g=panel_geometry(i,controls,scalp);roots=g['roots'];tips=g['tips']
            self.line('RootLine',g['dense'],mat=self.edge,dashed=i.dashed)
            self.line('CutLine',tips,mat=self.edge,dashed=i.dashed)
            for j in [0,-1]:self.line('PanelBorder',[roots[j],tips[j]],mat=self.edge,dashed=i.dashed)
            if i.style in {'STRANDS','TINT','RIBBONS'}:
                for a,b in zip(roots,tips):
                    self.line('Strand',[a,b],dashed=i.dashed)
                    if i.arrow:self.arrow(a,b)
            if i.style in {'TINT','RIBBONS'}:
                verts=roots+tips;count=len(roots)
                faces=[(j,j+1,count+j+1,count+j) for j in range(count-1) if i.style=='TINT' or j%2==0]
                data=bpy.data.meshes.new('PanelFace');data.from_pydata(verts,[],faces);data.update()
                self.attach('PanelFace',data,color_material(i.edge_color,i.opacity),'FILL')
            mid=len(roots)//2
            if i.show_angle:self.angle(roots[mid],*g['basis'],i.elevation,g['lengths'][mid])
            if i.show_length:self.text(f"{g['lengths'][mid]*100:.1f} cm",tips[mid]+Vector((0,0,.008)),'INFO')
            return g
        return None
