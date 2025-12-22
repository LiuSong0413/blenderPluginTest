bl_info = {
    "name": "辅助大师 (Modeling Assistant Master)",
    "author": "Your Name",
    "version": (2, 6), # 修复导出器报错，新增智能导出路径
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > 建模辅助",
    "description": "倒角权重、一键精简、法线加权 + 智能路径 GLB 快速导出器",
    "category": "Mesh",
}

import bpy
import bmesh
import os


# ---------------------------------------------------------
# 编辑模式：倒角权重设定
# ---------------------------------------------------------
class MESH_OT_set_bevel_weight_edit(bpy.types.Operator):
    """直接设置选中边的 Bevel Weight"""
    bl_idname = "mesh.set_bevel_weight_edit"
    bl_label = "应用倒角权重"
    bl_options = {'REGISTER', 'UNDO'}

    weight: bpy.props.FloatProperty(
        name="倒角权重",
        min=0.0, max=1.0, default=1.0,
        description="设置选中边的倒角权重"
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        obj = context.object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        layer = bm.edges.layers.float.get("bevel_weight_edge")
        if not layer:
            layer = bm.edges.layers.float.new("bevel_weight_edge")

        sel_edges = [e for e in bm.edges if e.select]
        if not sel_edges:
            self.report({'WARNING'}, "未选择任何边")
            bm.free()
            return {'CANCELLED'}

        for e in sel_edges:
            e[layer] = self.weight

        bmesh.update_edit_mesh(me)
        bm.free()
        self.report({'INFO'}, f"已设置 {len(sel_edges)} 条边的倒角权重 = {self.weight}")
        return {'FINISHED'}


# ---------------------------------------------------------
# 对象模式：一键精简
# ---------------------------------------------------------
class OBJECT_OT_add_decimate_modifier(bpy.types.Operator):
    """为所选对象添加精简修改器"""
    bl_idname = "object.add_decimate_modifier"
    bl_label = "一键精简"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        selected_objs = context.selected_editable_objects
        if not selected_objs:
            self.report({'WARNING'}, "未选择任何对象")
            return {'CANCELLED'}

        ratio = context.scene.decimate_ratio
        count = 0
        for obj in selected_objs:
            if obj.type != 'MESH': continue
            dec = obj.modifiers.new(name="QuickDecimate", type='DECIMATE')
            dec.ratio = ratio
            count += 1
        self.report({'INFO'}, f"已为 {count} 个对象添加精简修改器")
        return {'FINISHED'}


# ---------------------------------------------------------
# 对象模式：法线加权
# ---------------------------------------------------------
class OBJECT_OT_add_weighted_normal(bpy.types.Operator):
    """为所选对象添加加权法线修改器"""
    bl_idname = "object.add_weighted_normal"
    bl_label = "一键法线加权"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        selected_objs = context.selected_editable_objects
        if not selected_objs:
            self.report({'WARNING'}, "未选择任何对象")
            return {'CANCELLED'}

        count = 0
        for obj in selected_objs:
            if obj.type != 'MESH': continue
            wn = obj.modifiers.new(name="WeightedNormal_Auto", type='WEIGHTED_NORMAL')
            wn.mode = 'FACE_AREA_WITH_ANGLE'
            wn.keep_sharp = True
            count += 1
        self.report({'INFO'}, f"已为 {count} 个对象添加法线加权修改器")
        return {'FINISHED'}


# ---------------------------------------------------------
# 对象模式：GLB 导出器 (智能路径修复版)
# ---------------------------------------------------------
class OBJECT_OT_export_selected_glb(bpy.types.Operator):
    """导出选中的对象为 GLB 文件"""
    bl_idname = "object.export_selected_glb"
    bl_label = "导出 GLB"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and len(context.selected_objects) > 0

    def execute(self, context):
        scn = context.scene
        props = scn.modeling_assistant_props

        # 1. 确定文件名
        target_name = props.export_custom_name if props.use_custom_name else context.selected_objects[0].name
        safe_name = "".join(c for c in target_name if c.isalnum() or c in (' ', '_', '-')).strip() or "export"

        # 2. 确定文件夹路径 (核心修改)
        blend_path = bpy.data.filepath
        if props.use_custom_path:
            export_dir = props.export_custom_path
        else:
            if not blend_path:
                # 如果 .blend 文件未保存，使用桌面/文档作为 fallback 并自动创建文件夹
                fallback_dir = os.path.join(os.path.expanduser("~"), "Documents", "Blender_Exports")
                export_dir = fallback_dir
            else:
                # 默认在 .blend 文件旁新建 "Exports" 文件夹
                export_dir = os.path.join(os.path.dirname(blend_path), "Exports")

        # 确保文件夹存在
        if not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir)
            except OSError as e:
                self.report({'ERROR'}, f"无法创建文件夹: {export_dir}\n{e}")
                return {'CANCELLED'}

        # 3. 组合最终完整路径
        final_path = os.path.join(export_dir, f"{safe_name}.glb")

        # 4. 构建导出参数字典 (保持稳定)
        export_args = {
            'filepath': final_path,
            'export_format': 'GLB',
            'use_selection': True,

            # --- 几何体 (Meshes) ---
            'export_apply': props.export_apply_transforms,
            'export_morph': props.export_shape_keys,
            'export_morph_normal': props.export_shape_keys_normal,
            'export_morph_tangent': props.export_shape_keys_tangent,
            'export_attributes': props.export_custom_attributes,

            # --- 拓扑与压缩 ---
            'export_draco_mesh_compression_enable': props.export_draco,

            # --- 材质与纹理 ---
            'export_image_format': props.export_image_format,
            'export_materials': props.export_materials_mode,
            'export_texcoords': props.export_uvs,
            'export_normals': props.export_normals,
            'export_tangents': props.export_tangents,

            # --- 动画 (Animations) ---
            'export_animations': props.export_animations,
            'export_animation_mode': props.export_animation_mode,
            'export_force_sampling': props.export_force_sampling,
            'export_nla_strips': props.export_nla_strips,

            # --- 动画优化 ---
            'export_optimize_animation_size': props.export_optimize_animation_size,
            'export_anim_single_armature': props.export_anim_single_armature,
            'export_reset_pose_bones': props.export_reset_pose_bones,

            # --- 骨骼 (Skinning) ---
            'export_skins': props.export_skins,
            'export_all_influences': props.export_all_influences,

            # --- 场景 ---
            'export_cameras': props.export_cameras,
            'export_lights': props.export_lights,
            'export_extras': props.export_extras,
            'export_yup': True,
        }

        # 5. 执行导出
        try:
            bpy.ops.export_scene.gltf(**export_args)
        except TypeError as e:
            self.report({'ERROR'}, f"参数错误: {str(e)}\n建议检查导出器版本或手动导出。")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"导出失败: {str(e)}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"GLB 导出成功: {final_path}")
        return {'FINISHED'}


# ---------------------------------------------------------
# UI 面板定义
# ---------------------------------------------------------

class VIEW3D_PT_bevel_weight_panel(bpy.types.Panel):
    bl_label = "倒角权重快速设置"
    bl_idname = "VIEW3D_PT_bevel_weight_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        if context.mode != 'EDIT_MESH':
            layout.label(text="请进入编辑模式", icon='ERROR')
            return

        layout.prop(context.scene, "bw_value", slider=True)
        op = layout.operator("mesh.set_bevel_weight_edit", text="应用倒角权重")
        op.weight = context.scene.bw_value


class VIEW3D_PT_modeling_assist_panel(bpy.types.Panel):
    bl_label = "建模辅助大师"
    bl_idname = "VIEW3D_PT_modeling_assist_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        if context.mode != 'OBJECT':
            layout.label(text="请进入对象模式", icon='ERROR')
            return

        # 建模工具组
        box = layout.box()
        box.label(text="建模工具", icon='MODIFIER')
        col = box.column(align=True)
        col.prop(context.scene, "decimate_ratio", slider=True)
        col.operator("object.add_decimate_modifier", text="一键精简")
        col.separator()
        col.operator("object.add_weighted_normal", text="一键法线加权")

        layout.separator()


class VIEW3D_PT_glb_exporter(bpy.types.Panel):
    bl_label = "GLB 快速导出"
    bl_idname = "VIEW3D_PT_glb_exporter"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        if context.mode != 'OBJECT': return

        scn = context.scene
        props = scn.modeling_assistant_props

        layout.label(text="导出设置", icon='EXPORT')

        # --- 路径设置 (新增) ---
        box = layout.box()
        box.label(text="输出路径", icon='FILE_FOLDER')
        col = box.column(align=True)

        row = col.row()
        row.prop(props, "use_custom_path", text="自定义路径")

        if props.use_custom_path:
            col.prop(props, "export_custom_path", text="")
            # 提示按钮：打开文件夹
            if props.export_custom_path:
                op = col.operator("wm.path_open", text="打开输出文件夹")
                op.filepath = props.export_custom_path
        else:
            # 显示默认路径的提示
            blend_path = bpy.data.filepath
            if blend_path:
                default_dir = os.path.join(os.path.dirname(blend_path), "Exports")
                col.label(text=f"默认: {default_dir}", icon='INFO')
            else:
                col.label(text="默认: 保存 .blend 文件后将创建 'Exports' 文件夹", icon='INFO')

        # --- 文件名设置 ---
        col = box.column(align=True)
        row = col.row()
        row.prop(props, "use_custom_name", text="自定义文件名")
        if props.use_custom_name:
            col.prop(props, "export_custom_name", text="")

        # --- 网格 & 几何体 ---
        box = layout.box()
        box.label(text="1. 网格 & 几何体", icon='MESH_DATA')
        col = box.column(align=True)
        col.prop(props, "export_apply_transforms", text="应用变换")

        # 形态键
        row = box.row()
        row.prop(props, "export_shape_keys", text="形态键")
        if props.export_shape_keys:
            sub = box.column(align=True)
            sub.prop(props, "export_shape_keys_normal", text="形态键法线")
            sub.prop(props, "export_shape_keys_tangent", text="形态键切线")

        # 压缩
        box.prop(props, "export_draco", text="Draco 压缩")

        # --- 材质 & 纹理 ---
        box = layout.box()
        box.label(text="2. 材质 & 纹理", icon='MATERIAL')
        col = box.column(align=True)
        col.prop(props, "export_materials_mode", text="材质模式")
        col.prop(props, "export_image_format", text="图片格式")
        col.prop(props, "export_uvs", text="UVs")
        col.prop(props, "export_normals", text="法线")

        row = col.row()
        row.prop(props, "export_tangents", text="切线 (Tangents)")
        row.enabled = props.export_normals

        # --- 动画 (Animations) ---
        box = layout.box()
        box.label(text="3. 动画 (Animation)", icon='ANIM')
        col = box.column(align=True)

        col.prop(props, "export_animations", text="导出动画")

        if props.export_animations:
            col.separator()
            col.prop(props, "export_animation_mode", text="动画模式")
            col.prop(props, "export_force_sampling", text="强制采样 (Baking)")
            col.prop(props, "export_nla_strips", text="NLA 混合轨道")

            sub = col.column(align=True)
            sub.prop(props, "export_optimize_animation_size", text="优化动画体积")
            sub.prop(props, "export_anim_single_armature", text="单骨骼动画")
            sub.prop(props, "export_reset_pose_bones", text="重置骨骼姿态")

        # --- 骨骼 & 蒙皮 ---
        box = layout.box()
        box.label(text="4. 骨骼 & 蒙皮", icon='ARMATURE_DATA')
        col = box.column(align=True)
        col.prop(props, "export_skins", text="导出蒙皮")
        if props.export_skins:
            col.prop(props, "export_all_influences", text="所有影响 (All Influences)")

        # --- 高级 & 场景 ---
        box = layout.box()
        box.label(text="5. 高级 & 场景", icon='WORLD')
        col = box.column(align=True)
        col.prop(props, "export_cameras", text="相机")
        col.prop(props, "export_lights", text="灯光")
        col.prop(props, "export_extras", text="自定义属性 (Extras)")

        col.separator()
        col.label(text="* 坐标系: 强制 Y-Up", icon='INFO')

        # --- 执行按钮 ---
        layout.separator()
        layout.operator("object.export_selected_glb", text="执行导出 (GLB)", icon='FILE_TICK')


# ---------------------------------------------------------
# 属性组
# ---------------------------------------------------------
class ModelingAssistantProperties(bpy.types.PropertyGroup):
    # --- 路径 ---
    use_custom_path: bpy.props.BoolProperty(name="自定义路径", default=False)
    export_custom_path: bpy.props.StringProperty(name="导出路径", subtype='DIR_PATH', default="")

    # --- 基础 ---
    use_custom_name: bpy.props.BoolProperty(name="自定义名称", default=False)
    export_custom_name: bpy.props.StringProperty(name="导出文件名", default="MyModel")

    # --- 网格 & 几何体 ---
    export_apply_transforms: bpy.props.BoolProperty(name="应用变换", default=True)
    export_custom_attributes: bpy.props.BoolProperty(name="自定义属性", default=False)

    export_shape_keys: bpy.props.BoolProperty(name="形态键", default=True)
    export_shape_keys_normal: bpy.props.BoolProperty(name="形态键法线", default=False)
    export_shape_keys_tangent: bpy.props.BoolProperty(name="形态键切线", default=False)

    export_draco: bpy.props.BoolProperty(name="Draco 压缩", default=False)

    # --- 材质 & 纹理 ---
    export_materials_mode: bpy.props.EnumProperty(
        name="材质模式",
        items=[
            ('EXPORT', "全部导出", "导出所有材质和纹理"),
            ('PLACEHOLDER', "仅引用", "不导出纹理，只保留引用"),
            ('NONE', "无材质", "仅导出几何体"),
        ],
        default='EXPORT'
    )
    export_image_format: bpy.props.EnumProperty(
        name="图片格式",
        items=[
            ('AUTO', "自动", "根据源文件决定"),
            ('JPEG', "JPEG", "压缩率高，无透明"),
            ('PNG', "PNG", "高质量，有透明"),
        ],
        default='AUTO'
    )
    export_uvs: bpy.props.BoolProperty(name="导出 UVs", default=True)
    export_normals: bpy.props.BoolProperty(name="导出 法线", default=True)
    export_tangents: bpy.props.BoolProperty(name="导出 切线", default=False)

    # --- 动画 (Animations) ---
    export_animations: bpy.props.BoolProperty(name="导出动画", default=True)
    export_animation_mode: bpy.props.EnumProperty(
        name="动画模式",
        items=[
            ('ACTIVE_ACTIONS', "动作 (Actions)", "导出当前激活的动作"),
            ('NLA_TRACKS', "NLA 轨道", "导出 NLA 轨道混合结果"),
        ],
        default='ACTIVE_ACTIONS'
    )
    export_force_sampling: bpy.props.BoolProperty(name="强制采样 (Baking)", default=True)
    export_nla_strips: bpy.props.BoolProperty(name="NLA 混合", default=False)
    export_optimize_animation_size: bpy.props.BoolProperty(name="优化动画体积", default=True)
    export_anim_single_armature: bpy.props.BoolProperty(name="单骨骼动画", default=False)
    export_reset_pose_bones: bpy.props.BoolProperty(name="重置骨骼姿态", default=False)

    # --- 骨骼 & 蒙皮 (Skinning) ---
    export_skins: bpy.props.BoolProperty(name="导出蒙皮 (骨骼)", default=True)
    export_all_influences: bpy.props.BoolProperty(name="所有影响 (All Influences)", default=False)

    # --- 高级 & 场景 ---
    export_cameras: bpy.props.BoolProperty(name="导出相机", default=False)
    export_lights: bpy.props.BoolProperty(name="导出灯光", default=False)
    export_extras: bpy.props.BoolProperty(name="导出自定义属性 (Extras)", default=False)


# ---------------------------------------------------------
# 注册
# ---------------------------------------------------------
classes = (
    ModelingAssistantProperties,
    MESH_OT_set_bevel_weight_edit,
    VIEW3D_PT_bevel_weight_panel,
    OBJECT_OT_add_decimate_modifier,
    OBJECT_OT_add_weighted_normal,
    OBJECT_OT_export_selected_glb,
    VIEW3D_PT_modeling_assist_panel,
    VIEW3D_PT_glb_exporter,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.modeling_assistant_props = bpy.props.PointerProperty(type=ModelingAssistantProperties)
    bpy.types.Scene.bw_value = bpy.props.FloatProperty(name="倒角权重", min=0.0, max=1.0, default=1.0)
    bpy.types.Scene.decimate_ratio = bpy.props.FloatProperty(name="精简比率", min=0.0, max=1.0, default=0.1)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    del bpy.types.Scene.modeling_assistant_props
    del bpy.types.Scene.bw_value
    del bpy.types.Scene.decimate_ratio


if __name__ == "__main__":
    register()
