"""v0.3: project-local, Chinese scalp diagram editor and interactive picking."""
import json
import uuid
from pathlib import Path
import bpy
from bpy_extras import view3d_utils
from bpy_extras.io_utils import ExportHelper
from mathutils import Vector
from . import editor_geometry as geo
from .view import cameras

KINDS=[('SURFACE','貼頭皮線','沿頭皮點幾個位置，Enter 完成'),('PANEL','提拉髮片','先點出髮片根部的分線'),
       ('RAY','單根提拉線','點一個毛根位置'),('GUIDE','空間輔助線','第一點可在頭皮，後續點在同一觀看平面'),
       ('POINT','頭皮點位','點一個位置，可自行命名'),('FAN','角度扇形','點一個位置，顯示0到180度')]
NAMES={k:n for k,n,_ in KINDS}
FIELDS=('name','kind','controls','visible','reference','elevation','swivel','length_cm','end_length_cm','cut_mode',
        'cut_angle','strands','style','opacity','width_mm','color','edge_color','dashed','arrow','closed',
        'show_angle','show_length','point_mm','label_mm','label_dx','label_dz')

def controls(item):return [Vector(p) for p in json.loads(item.controls)]
def set_controls(item,points):item.controls=json.dumps([list(p) for p in points])
def current(scene):
    return scene.hd_items[scene.hd_item_index] if 0<=scene.hd_item_index<len(scene.hd_items) else None

def owned(scene,uid):return [o for o in scene.objects if o.get('hd_editor_id')==uid]

def refresh_handles(self,context):
    if not context or not hasattr(context.scene,'hd_editor'):return
    scene=context.scene
    geo.erase(owned(scene,'__CONTROLS__'))
    i=current(scene)
    if i is None or not scene.hd_editor.show_handles:return
    from types import SimpleNamespace
    stub=SimpleNamespace(uid='__CONTROLS__',color=(.01,.3,.7),edge_color=(.01,.3,.7),width_mm=.6,point_mm=3,label_mm=4)
    d=geo.Drawing(stub)
    for j,p in enumerate(controls(i)):
        d.dot(p);d.text(str(j+1),p+Vector((0,0,.006)))
    for o in d.objects:o.hide_render=True

def visibility(self,context):
    if not context or not hasattr(context.scene,'hd_items'):return
    scene=context.scene;s=scene.hd_editor
    by_id={i.uid:i for i in scene.hd_items}
    for obj in scene.objects:
        item=by_id.get(obj.get('hd_editor_id'))
        if item is None:continue
        visible=item.visible
        if item.kind=='POINT':visible=visible and s.show_points
        if obj.get('hd_role')=='LABEL':visible=visible and s.show_labels
        obj.hide_viewport=not visible;obj.hide_render=not visible
    for name,on in [('HD_TEACH_SECTIONS',s.show_grid),('HD_TEACH_HAIRLINE',s.show_hairline),('HD_TEACH_SCALP',s.show_scalp)]:
        c=bpy.data.collections.get(name)
        if c:c.hide_viewport=not on;c.hide_render=not on

def rebuild(scene,item):
    old=owned(scene,item.uid)
    drawing=geo.Drawing(item)
    try:
        result=drawing.build(controls(item),geo.Scalp())
    except Exception:
        geo.erase(drawing.objects)
        raise
    geo.erase(old)
    item.built=json.dumps({k:list(getattr(item,k)) if k in {'color','edge_color'} else getattr(item,k) for k in FIELDS},ensure_ascii=False)
    visibility(None,bpy.context)
    refresh_handles(None,bpy.context)
    return result

def add_item(scene,kind,points,name=None,**settings):
    item=scene.hd_items.add();item.uid=uuid.uuid4().hex;item.kind=kind
    item.name=name or NAMES[kind]+str(sum(i.kind==kind for i in scene.hd_items))
    set_controls(item,points)
    for key,value in settings.items():setattr(item,key,value)
    try:rebuild(scene,item)
    except Exception:
        scene.hd_items.remove(len(scene.hd_items)-1)
        raise
    scene.hd_item_index=len(scene.hd_items)-1
    return item

def remove_item(scene,index):
    item=scene.hd_items[index];geo.erase(owned(scene,item.uid));scene.hd_items.remove(index)
    scene.hd_item_index=min(index,len(scene.hd_items)-1)

def load_font():
    if not bpy.data.fonts.get('HD_CHINESE'):
        path=Path(__file__).resolve().parent/'assets/vendor/noto/NotoSansCJKtc-Regular.otf'
        if path.exists():
            f=bpy.data.fonts.load(str(path));f.name='HD_CHINESE';f.pack()

def presets(scene):
    """Approximate educational landmarks, deliberately editable and not universal codes."""
    from .teaching import point,boundary
    from .config import REFERENCE_BP_ELEVATION
    definitions=[('前中點',0,boundary(0)),('頂點',0,89.9),('黃金點（示意）',180,57),('枕骨點（示意）',180,REFERENCE_BP_ELEVATION),('頸背點',180,boundary(180))]
    for sign,side in [(1,'左'),(-1,'右')]:
        definitions += [(side+'前側點',sign*65,boundary(65)),(side+'耳上點',sign*90,boundary(90)),(side+'耳後點',sign*118,boundary(118))]
    for name,az,el in definitions:
        if any(i.kind=='POINT' and i.name==name for i in scene.hd_items):continue
        add_item(scene,'POINT',[point(az,el)[0]],name,color=(.025,.23,.26),label_mm=4.3)

def fit_camera(scene):
    bpy.context.view_layer.update();camera=scene.camera
    inv=camera.matrix_world.inverted();points=[]
    for obj in scene.objects:
        if obj.type not in {'MESH','CURVE','FONT'} or obj.hide_render:continue
        if any(c.hide_render for c in obj.users_collection):continue
        for p in obj.bound_box:points.append(inv@(obj.matrix_world@Vector(p)))
    if not points:return
    lo=[min(p[j] for p in points) for j in range(2)];hi=[max(p[j] for p in points) for j in range(2)]
    shift=Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0))
    camera.location+=camera.matrix_world.to_3x3()@shift
    aspect=scene.render.resolution_x/scene.render.resolution_y
    camera.data.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*aspect)*1.2

def camera_view(context,key,fit=True):
    cameras.set_active(key)
    context.scene.hd_editor.camera=key
    if fit:fit_camera(context.scene)
    if context.screen:
        for area in context.screen.areas:
            if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'

class HDElement(bpy.types.PropertyGroup):
    uid:bpy.props.StringProperty()
    name:bpy.props.StringProperty(name='名稱',default='新元素')
    kind:bpy.props.EnumProperty(items=KINDS)
    controls:bpy.props.StringProperty(default='[]')
    built:bpy.props.StringProperty(default='')
    visible:bpy.props.BoolProperty(name='顯示',default=True,update=visibility)
    reference:bpy.props.EnumProperty(name='角度基準',items=[('LOCAL','各毛根頭皮','每條髮束按自己的頭皮法線提拉'),('CENTER','髮片中心頭皮（平行提拉）','整片使用中心毛根的方向'),('WORLD','垂直向下為0°','0向下，90水平，180向上；方向由水平轉向決定')],default='CENTER')
    elevation:bpy.props.FloatProperty(name='提拉角度（度）',min=0,max=180,default=90)
    swivel:bpy.props.FloatProperty(name='轉向（度）',min=-180,max=180,default=0)
    length_cm:bpy.props.FloatProperty(name='髮長（公分）',min=.1,max=30,default=7)
    end_length_cm:bpy.props.FloatProperty(name='末端髮長（公分）',min=.1,max=30,default=10)
    cut_mode:bpy.props.EnumProperty(name='髮尾形狀',items=[('EQUAL','等長','所有髮束等長'),('TAPER','兩端不同長','沿分線順序，從髮長漸變到末端髮長'),('PLANE','平面切口','髮束與獨立平面相交；角度以中央髮束為基準')],default='EQUAL')
    cut_angle:bpy.props.FloatProperty(name='切口角度（度）',min=5,max=175,default=90)
    strands:bpy.props.IntProperty(name='髮束線數量',min=2,max=40,default=9)
    style:bpy.props.EnumProperty(name='髮片畫法',items=[('OUTLINE','只有外框',''),('STRANDS','外框＋髮束線',''),('TINT','半透明色面＋髮束線',''),('RIBBONS','間隔色帶＋髮束線','')],default='STRANDS')
    opacity:bpy.props.FloatProperty(name='色面濃度',min=.02,max=.8,default=.16)
    width_mm:bpy.props.FloatProperty(name='線粗（毫米）',min=.15,max=3,default=.65)
    color:bpy.props.FloatVectorProperty(name='線／點顏色',subtype='COLOR',size=3,min=0,max=1,default=(.045,.07,.095))
    edge_color:bpy.props.FloatVectorProperty(name='髮片外框／色面',subtype='COLOR',size=3,min=0,max=1,default=(.78,.08,.18))
    dashed:bpy.props.BoolProperty(name='虛線',default=False)
    arrow:bpy.props.BoolProperty(name='箭頭',default=False)
    closed:bpy.props.BoolProperty(name='首尾連成封閉分區',default=False)
    show_angle:bpy.props.BoolProperty(name='顯示提拉角度弧線',default=False)
    show_length:bpy.props.BoolProperty(name='顯示髮長',default=False)
    point_mm:bpy.props.FloatProperty(name='點的大小（毫米）',default=3,min=1,max=8)
    label_mm:bpy.props.FloatProperty(name='文字大小（毫米）',default=4.5,min=2,max=12)
    label_dx:bpy.props.FloatProperty(name='文字左右偏移（毫米）',default=0,min=-40,max=40)
    label_dz:bpy.props.FloatProperty(name='文字上下偏移（毫米）',default=6,min=-40,max=40)

class HDEditorSettings(bpy.types.PropertyGroup):
    show_handles:bpy.props.BoolProperty(name='顯示所選項目的控制點編號（不輸出）',default=False,update=refresh_handles)
    show_points:bpy.props.BoolProperty(name='頭皮點位',default=True,update=visibility)
    show_labels:bpy.props.BoolProperty(name='點位名稱',default=True,update=visibility)
    show_grid:bpy.props.BoolProperty(name='初始結構線（鎖定）',default=False,update=visibility)
    show_hairline:bpy.props.BoolProperty(name='髮際線',default=True,update=visibility)
    show_scalp:bpy.props.BoolProperty(name='灰色頭皮',default=True,update=visibility)
    control_index:bpy.props.IntProperty(name='第幾個控制點',default=1,min=1)
    camera:bpy.props.EnumProperty(name='觀看方向',items=[('front','正面',''),('front_left_45','前左斜看',''),('left','左側面',''),('back_left_45','後左斜看',''),('back','後面',''),('back_right_45','後右斜看',''),('right','右側面',''),('front_right_45','前右斜看',''),('top','頭頂','')],default='front_left_45')

class HD_UL_elements(bpy.types.UIList):
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        icons={'POINT':'DOT','SURFACE':'CURVE_DATA','PANEL':'MOD_CLOTH','RAY':'EMPTY_SINGLE_ARROW','GUIDE':'CURVE_PATH','FAN':'DRIVER_ROTATIONAL_DIFFERENCE'}
        row=layout.row(align=True);row.label(text=item.name,icon=icons[item.kind]);row.prop(item,'visible',text='',emboss=False,icon='HIDE_OFF' if item.visible else 'HIDE_ON')

class HD_OT_edit_apply(bpy.types.Operator):
    bl_idname='hd.edit_apply';bl_label='套用到這一項';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        item=current(context.scene)
        if item is None:return {'CANCELLED'}
        try:rebuild(context.scene,item)
        except (ValueError,RuntimeError) as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        self.report({'INFO'},'已更新：'+item.name);return {'FINISHED'}

class HD_OT_edit_delete(bpy.types.Operator):
    bl_idname='hd.edit_delete';bl_label='刪除這一項';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        if current(context.scene) is None:return {'CANCELLED'}
        remove_item(context.scene,context.scene.hd_item_index);return {'FINISHED'}

class HD_OT_edit_duplicate(bpy.types.Operator):
    bl_idname='hd.edit_duplicate';bl_label='複製這一項';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        item=current(context.scene)
        if item is None:return {'CANCELLED'}
        values={k:list(getattr(item,k)) if k in {'color','edge_color'} else getattr(item,k) for k in FIELDS if k not in {'name','kind','controls'}}
        add_item(context.scene,item.kind,controls(item),item.name+' 副本',**values);return {'FINISHED'}

class HD_OT_convert_panel(bpy.types.Operator):
    bl_idname='hd.convert_panel';bl_label='從這條線新增髮片';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        i=current(context.scene)
        if i is None or i.kind!='SURFACE':return {'CANCELLED'}
        try:add_item(context.scene,'PANEL',controls(i),i.name+' 髮片')
        except ValueError as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class HD_OT_edit_point_remove(bpy.types.Operator):
    bl_idname='hd.edit_point_remove';bl_label='刪除這個控制點';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        item=current(context.scene)
        if item is None:return {'CANCELLED'}
        pts=controls(item);index=context.scene.hd_editor.control_index-1
        if len(pts)<=2 or not 0<=index<len(pts):
            self.report({'WARNING'},'線條至少保留兩點；若要整條刪掉，請按刪除這一項。');return {'CANCELLED'}
        old=item.controls;pts.pop(index);set_controls(item,pts)
        try:rebuild(context.scene,item)
        except ValueError as e:item.controls=old;self.report({'ERROR'},str(e));return {'CANCELLED'}
        context.scene.hd_editor.control_index=min(index+1,len(pts));return {'FINISHED'}

class HD_OT_preset_points(bpy.types.Operator):
    bl_idname='hd.preset_points';bl_label='加入常用點位（可改名／位置）';bl_options={'REGISTER','UNDO'}
    def execute(self,context):presets(context.scene);return {'FINISHED'}

class HD_OT_editor_view(bpy.types.Operator):
    bl_idname='hd.editor_view';bl_label='切換視角／完整置中';bl_options={'REGISTER','UNDO'}
    def execute(self,context):camera_view(context,context.scene.hd_editor.camera);return {'FINISHED'}

class HD_OT_editor_export(bpy.types.Operator,ExportHelper):
    bl_idname='hd.editor_export';bl_label='存成教材圖片（PNG）'
    filename_ext='.png'
    filter_glob:bpy.props.StringProperty(default='*.png',options={'HIDDEN'})
    fit:bpy.props.BoolProperty(name='自動完整置中',default=True)
    def execute(self,context):
        from .output.render import render_diagram
        if self.fit:fit_camera(context.scene)
        try:render_diagram(output_path=self.filepath,width=2000,height=2000,transparent=True)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        self.report({'INFO'},'圖片已儲存：'+self.filepath)
        return {'FINISHED'}

class HD_OT_editor_pick(bpy.types.Operator):
    bl_idname='hd.editor_pick';bl_label='到頭皮上點選';bl_options={'REGISTER','UNDO','BLOCKING'}
    kind:bpy.props.EnumProperty(items=KINDS,default='SURFACE')
    operation:bpy.props.EnumProperty(items=[('ADD','新增',''),('REDRAW','重畫',''),('MOVE','移動控制點',''),('INSERT','插入控制點','')],default='ADD')

    def invoke(self,context,event):
        if context.area.type!='VIEW_3D' or context.mode!='OBJECT':
            self.report({'ERROR'},'請在看頭的視窗操作，並先回到物件模式。');return {'CANCELLED'}
        try:self.scalp=geo.Scalp()
        except ValueError as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        self.area=context.area;self.region=next(r for r in self.area.regions if r.type=='WINDOW')
        self.uid=None;self.original=[]
        if self.operation!='ADD':
            item=current(context.scene)
            if item is None:return {'CANCELLED'}
            self.uid=item.uid;self.kind=item.kind;self.original=controls(item)
            index=context.scene.hd_editor.control_index-1
            if self.operation in {'MOVE','INSERT'} and not 0<=index<len(self.original):
                self.report({'ERROR'},'控制點編號超過這條線的點數。');return {'CANCELLED'}
            self.edit_index=index
        self.points=[];self.preview=[];self.navigating=False
        self.area.header_text_set('左鍵點頭皮 | Enter 完成 | Backspace 退一點 | Esc 取消 | 中鍵可轉頭')
        context.window.cursor_modal_set('CROSSHAIR');context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def finish(self,context,cancel=False):
        geo.erase(self.preview);self.preview=[]
        self.area.header_text_set(None);context.window.cursor_modal_restore();self.area.tag_redraw()
        if cancel:return {'CANCELLED'}
        try:
            if self.operation=='ADD':add_item(context.scene,self.kind,self.points)
            else:
                item=next((i for i in context.scene.hd_items if i.uid==self.uid),None)
                if item is None:return {'CANCELLED'}
                pts=self.points
                if self.operation=='MOVE':pts=self.original[:];pts[self.edit_index]=self.points[0]
                elif self.operation=='INSERT':pts=self.original[:];pts.insert(self.edit_index+1,self.points[0])
                old=item.controls;set_controls(item,pts)
                try:rebuild(context.scene,item)
                except Exception:item.controls=old;raise
        except (ValueError,RuntimeError) as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        self.report({'INFO'},'完成。可在右側調整這一項。');return {'FINISHED'}

    def update_preview(self,context):
        geo.erase(self.preview);self.preview=[]
        if not self.points:return
        # Temporary Blender geometry, removed on both completion and cancellation.
        from types import SimpleNamespace
        stub=SimpleNamespace(uid='PREVIEW',color=(.03,.38,.7),edge_color=(.03,.38,.7),width_mm=.8,point_mm=2.5)
        draw=geo.Drawing(stub)
        for p in self.points:draw.dot(Vector(p))
        if len(self.points)>1:
            try:path=self.points if self.kind=='GUIDE' else self.scalp.path(self.points)
            except ValueError:path=self.points
            draw.line('Preview',path)
        self.preview=draw.objects
        self.area.header_text_set(f'已點 {len(self.points)} 點 | 左鍵繼續 | Enter 完成 | Backspace 退一點 | Esc 取消')

    def modal(self,context,event):
        if context.scene.get('hd_ui_debug') and event.type in {'LEFTMOUSE','RET','NUMPAD_ENTER'}:
            print('MODAL_EVENT',event.type,event.value,event.mouse_x,event.mouse_y,len(self.points),flush=True)
        if event.type=='ESC':return self.finish(context,True)
        if event.type=='MIDDLEMOUSE':
            self.navigating=event.value=='PRESS'
            return {'PASS_THROUGH'}
        if self.navigating and event.type=='MOUSEMOVE':return {'PASS_THROUGH'}
        if event.type in {'WHEELUPMOUSE','WHEELDOWNMOUSE','NDOF_MOTION'} or (event.type.startswith('NUMPAD') and event.type!='NUMPAD_ENTER'):
            return {'PASS_THROUGH'}
        if event.type in {'RET','NUMPAD_ENTER'} and event.value=='PRESS':
            minimum=1 if self.kind in {'POINT','RAY','FAN'} or self.operation in {'MOVE','INSERT'} else 2
            if len(self.points)>=minimum:return self.finish(context)
            self.report({'WARNING'},'請先點至少兩個位置。');return {'RUNNING_MODAL'}
        if event.type=='BACK_SPACE' and event.value=='PRESS':
            if self.points:self.points.pop();self.update_preview(context)
            return {'RUNNING_MODAL'}
        if event.type=='LEFTMOUSE' and event.value=='PRESS':
            r=self.region;xy=(event.mouse_x-r.x,event.mouse_y-r.y)
            if not (0<=xy[0]<r.width and 0<=xy[1]<r.height):return {'RUNNING_MODAL'}
            rv=self.area.spaces.active.region_3d
            origin=view3d_utils.region_2d_to_origin_3d(r,rv,xy,clamp=5)
            direction=view3d_utils.region_2d_to_vector_3d(r,rv,xy)
            # Orthographic camera utility may start at the clip-volume midpoint,
            # behind this small head. Rebase along the same ray in front of it.
            if not rv.is_perspective:
                origin+=direction*((self.scalp.center-origin).dot(direction)-2.0)
            hit=self.scalp.pick(origin,direction)
            if context.scene.get('hd_ui_debug'):print('PICK',xy,tuple(origin),tuple(direction),hit,flush=True)
            if self.kind=='GUIDE':
                if self.operation in {'MOVE','INSERT'}:depth=self.original[self.edit_index]
                else:depth=self.points[0] if self.points else (hit[0] if hit else Vector((0,0,0)))
                p=view3d_utils.region_2d_to_location_3d(r,rv,xy,depth)
            elif hit:p=hit[0]
            else:
                self.report({'WARNING'},'請點在看得到的頭皮；臉、耳朵和背景不能放頭皮線。');return {'RUNNING_MODAL'}
            if self.points and (p-self.points[-1]).length<.0001:return {'RUNNING_MODAL'}
            self.points.append(p)
            if self.kind in {'POINT','RAY','FAN'} or self.operation in {'MOVE','INSERT'}:return self.finish(context)
            self.update_preview(context);return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}

class HD_PT_editor(bpy.types.Panel):
    bl_label='自由頭圖編輯器 v0.3';bl_idname='HD_PT_editor';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Hair Diagram'
    def draw(self,context):
        l=self.layout;s=context.scene.hd_editor
        if not bpy.data.objects.get('HD_SCALP_SURFACE'):
            l.label(text='請用「開啟教材模型」啟動。');return
        l.prop(s,'camera',text='觀看方向');l.operator('hd.editor_view')
        l.operator('hd.editor_export',icon='IMAGE_DATA')
        l.separator()
        l.label(text='1. 新增 → 點頭皮 → Enter 完成')
        for pair in [('POINT','SURFACE'),('RAY','PANEL'),('GUIDE','FAN')]:
            row=l.row(align=True)
            for kind in pair:
                op=row.operator('hd.editor_pick',text='＋'+NAMES[kind]);op.kind=kind
        l.label(text='Esc 取消；Backspace 退一點')
        l.separator();l.label(text='2. 點清單選項目；眼睛開關顯示')
        l.template_list('HD_UL_elements','',context.scene,'hd_items',context.scene,'hd_item_index',rows=6)
        row=l.row(align=True);row.operator('hd.edit_duplicate',text='複製');row.operator('hd.edit_delete',text='刪除')
        item=current(context.scene)
        if item:
            box=l.box();box.label(text=NAMES[item.kind]);box.prop(item,'name')
            box.operator('hd.edit_apply',icon='CHECKMARK')
            if item.kind in {'PANEL','RAY','FAN'}:
                box.prop(item,'reference');box.prop(item,'swivel')
                if item.reference=='WORLD':box.label(text='0向下／90水平／180向上')
                else:box.label(text='90°＝頭皮向外；頂點零向取前方')
                if item.kind!='FAN':box.prop(item,'elevation')
                box.prop(item,'length_cm')
            if item.kind=='PANEL':
                box.prop(item,'cut_mode')
                if item.cut_mode=='TAPER':box.prop(item,'end_length_cm')
                elif item.cut_mode=='PLANE':
                    box.prop(item,'cut_angle');box.label(text='90°切口＝垂直於中央髮束')
                box.prop(item,'style');box.prop(item,'strands')
                if item.style in {'TINT','RIBBONS'}:box.prop(item,'opacity')
                box.prop(item,'edge_color')
            box.prop(item,'color')
            if item.kind=='POINT':
                box.prop(item,'point_mm');box.prop(item,'label_mm')
                row=box.row(align=True);row.prop(item,'label_dx');row.prop(item,'label_dz')
            else:
                box.prop(item,'width_mm');row=box.row(align=True);row.prop(item,'dashed')
                if item.kind in {'GUIDE','RAY','PANEL','FAN'}:row.prop(item,'arrow')
                if item.kind=='SURFACE':box.prop(item,'closed');box.operator('hd.convert_panel')
                if item.kind in {'PANEL','RAY'}:
                    row=box.row(align=True);row.prop(item,'show_angle');row.prop(item,'show_length')
            box.operator('hd.edit_apply',icon='CHECKMARK')

class HD_PT_editor_controls(bpy.types.Panel):
    bl_label='移動位置／增減控制點';bl_idname='HD_PT_editor_controls';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Hair Diagram';bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        l=self.layout;i=current(context.scene)
        if not i:l.label(text='先在上方清單選一項。');return
        count=len(controls(i));l.label(text=f'這一項有 {count} 個控制點')
        l.prop(context.scene.hd_editor,'show_handles')
        l.prop(context.scene.hd_editor,'control_index')
        op=l.operator('hd.editor_pick',text='移動這一點 → 再點頭皮');op.operation='MOVE'
        if i.kind in {'SURFACE','PANEL','GUIDE'}:
            op=l.operator('hd.editor_pick',text='在這點後插入一點');op.operation='INSERT'
            l.operator('hd.edit_point_remove')
            op=l.operator('hd.editor_pick',text='重新點整條根線');op.operation='REDRAW'
        l.label(text='控制點順序＝當初點選順序')

class HD_PT_editor_visibility(bpy.types.Panel):
    bl_label='點位與背景開關';bl_idname='HD_PT_editor_visibility';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Hair Diagram';bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        l=self.layout;s=context.scene.hd_editor
        for key in ['show_points','show_labels','show_grid','show_hairline','show_scalp']:l.prop(s,key)
        l.operator('hd.preset_points');l.label(text='點位是可調示意，非各教材統一標準')

CLASSES=(HDElement,HDEditorSettings,HD_UL_elements,HD_OT_edit_apply,HD_OT_edit_delete,HD_OT_edit_duplicate,
         HD_OT_convert_panel,HD_OT_edit_point_remove,HD_OT_preset_points,HD_OT_editor_view,HD_OT_editor_pick,
         HD_OT_editor_export,HD_PT_editor,HD_PT_editor_controls,HD_PT_editor_visibility)

def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.hd_items=bpy.props.CollectionProperty(type=HDElement)
    bpy.types.Scene.hd_item_index=bpy.props.IntProperty(default=-1,update=refresh_handles)
    bpy.types.Scene.hd_editor=bpy.props.PointerProperty(type=HDEditorSettings)
    # Preferences registration runs with restricted scene data. The starter
    # already stores reference locks; scene builders also apply them explicitly.
    from . import course
    course.register()

def unregister():
    from . import course
    course.unregister()
    del bpy.types.Scene.hd_items;del bpy.types.Scene.hd_item_index;del bpy.types.Scene.hd_editor
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
