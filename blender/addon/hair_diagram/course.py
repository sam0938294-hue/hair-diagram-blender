"""Book-to-scene bridge. Lessons add independent objects; exports are snapshots."""
import json,os,textwrap,datetime,uuid
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[3]
BOOK=ROOT/'output/pdf'
def lessons():
    return json.loads((BOOK/'lessons.json').read_text(encoding='utf-8'))
LESSONS=lessons() if (BOOK/'lessons.json').exists() else []
CHOICES=[(str(i),f'第{i+2}頁｜{p["title"]}',p['lead']) for i,p in enumerate(LESSONS)]
def selected(s):return LESSONS[int(s.hd_course.lesson)]

class HDCourse(bpy.types.PropertyGroup):
    lesson:bpy.props.EnumProperty(name='教材題目',items=CHOICES)
    preset:bpy.props.EnumProperty(name='加入哪個範例',items=[('WORLD45','世界基準45°',''),('WORLD90','世界基準90°',''),('LOCAL90','頭皮局部90°',''),('SECTIONS','後區分線','')])
    note:bpy.props.StringProperty(name='這次改了什麼',default='')

class HD_OT_course_page(bpy.types.Operator):
    bl_idname='hd.course_page';bl_label='看這一頁教材'
    def execute(self,context):
        path=BOOK/'preview'/f'page-{int(context.scene.hd_course.lesson)+2:02}.png'
        if not path.exists():self.report({'ERROR'},'找不到教材頁面');return {'CANCELLED'}
        os.startfile(str(path));return {'FINISHED'}

class HD_OT_course_add(bpy.types.Operator):
    bl_idname='hd.course_add';bl_label='把範例加入頭模';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        from . import editor,teaching
        s=context.scene;kind=s.hd_course.preset;made=[]
        if not bpy.data.objects.get('HD_SCALP_SURFACE'):
            self.report({'ERROR'},'請先用「開啟教材模型」開啟頭模');return {'CANCELLED'}
        def pts(v):return [teaching.point(a,e)[0] for a,e in v]
        try:
            if kind=='SECTIONS':
                for e in [5,20,35,50]:
                    made.append(editor.add_item(s,'SURFACE',pts([(125,e),(145,e),(165,e),(180,e),(195,e),(215,e),(235,e)]),f'教材後區分線 {e}',color=(.02,.32,.36)).uid)
            else:
                made.append(editor.add_item(s,'PANEL',pts([(145,5),(145,25),(145,45)]),'教材 '+kind,reference='LOCAL' if kind=='LOCAL90' else 'WORLD',swivel=180,elevation=45 if kind=='WORLD45' else 90,length_cm=8,style='STRANDS',show_angle=False).uid)
            for i in s.hd_items:
                if i.uid in made:i['lesson_page']=int(s.hd_course.lesson)+2
            self.report({'INFO'},'已新增；在下方清單選取並修改。原有項目保留。')
            return {'FINISHED'}
        except Exception as e:
            for j in range(len(s.hd_items)-1,-1,-1):
                if s.hd_items[j].uid in made:editor.remove_item(s,j)
            self.report({'ERROR'},str(e));return {'CANCELLED'}

def export_snapshot(context):
    from . import editor
    from .api import render_diagram
    s=context.scene;p=selected(s);page=int(s.hd_course.lesson)+2
    target=ROOT/'output/course-runs'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]);target.mkdir(parents=True)
    # Apply pending UI values first so exported recipes describe exported geometry.
    for item in s.hd_items:editor.rebuild(s,item)
    editor.visibility(None,context)
    recipes=[]
    for item in s.hd_items:
        data={}
        for prop in item.bl_rna.properties:
            k=prop.identifier
            if k=='rna_type' or prop.type in {'POINTER','COLLECTION'}:continue
            value=getattr(item,k)
            data[k]=list(value) if getattr(prop,'is_array',False) else value
        recipes.append(data)
    old=(s.render.filepath,s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage)
    try:
        render_diagram(width=2000,height=2000,output_path=str(target/'head.png'))
        bpy.ops.wm.save_as_mainfile(filepath=str(target/'editable.blend'),copy=True)
    finally:
        s.render.filepath,s.render.resolution_x,s.render.resolution_y,s.render.resolution_percentage=old
    data={'page':page,'lesson':p,'note':s.hd_course.note,'camera':s.camera.name if s.camera else None,'items':recipes,'verified_haircut':False}
    (target/'parameters.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    (target/'教材頁.md').write_text('# '+p['title']+'\n\n'+p['lead']+'\n\n'+'\n\n'.join(p['body'])+'\n\n![我的頭圖](head.png)\n\n## 我的修改\n\n'+(s.hd_course.note or '未填寫')+'\n\n## 練習\n\n'+p['task']+'\n\n來源索引：'+p['refs']+'\n\n原教材頁碼：'+str(page)+'。本次為幾何示意，未經實剪驗證。\n\n重新編輯：先啟用專案工具，再開 editable.blend。',encoding='utf-8')
    return target

class HD_OT_course_export(bpy.types.Operator):
    bl_idname='hd.course_export';bl_label='存成我的教材範例（圖＋模型＋文字）'
    def execute(self,context):
        try:path=export_snapshot(context)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        os.startfile(str(path));self.report({'INFO'},'已存成新的教材資料夾');return {'FINISHED'}

class HD_PT_course(bpy.types.Panel):
    bl_label='教材練習｜選題 → 改圖 → 保存';bl_idname='HD_PT_course';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='教材練習'
    def draw(self,context):
        l=self.layout;s=context.scene
        if not LESSONS:l.label(text='請先建立教材範本');return
        l.prop(s.hd_course,'lesson');l.operator('hd.course_page',icon='IMAGE_DATA')
        p=selected(s);box=l.box()
        for t in textwrap.wrap(p['task'],14):box.label(text=t)
        l.label(text='範例會新增，已有線條不刪除')
        l.prop(s.hd_course,'preset');l.operator('hd.course_add',icon='ADD')
        l.label(text='切到 Hair Diagram 改參數並套用')
        l.prop(s.hd_course,'note');l.operator('hd.course_export',icon='FILE_TICK')
        l.label(text='保存為獨立版本，不改原書PDF')

CLASSES=(HDCourse,HD_OT_course_page,HD_OT_course_add,HD_OT_course_export,HD_PT_course)
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.hd_course=bpy.props.PointerProperty(type=HDCourse)
def unregister():
    del bpy.types.Scene.hd_course
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
