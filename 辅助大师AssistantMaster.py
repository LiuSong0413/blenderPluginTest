bl_info = {
    "name": "辅助大师 (Modeling Assistant Master)",
    "author": "Your Name",
    "version": (2, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Modeling Assistant",
    "description": "快速设置倒角权重，并在对象模式中一键加精简与法线加权修改器",
    "category": "Mesh",
}

import bpy
import bmesh


# ---------------------------------------------------------
# 编辑模式：倒角权重设定（替换）
# ---------------------------------------------------------
class MESH_OT_set_bevel_weight_edit(bpy.types.Operator):
    """直接设置选中边的 Bevel Weight"""
    bl_idname = "mesh.set_bevel_weight_edit"
    bl_label = "应用倒角权重"
    bl_options = {'REGISTER', 'UNDO'}

    weight: bpy.props.FloatProperty(
        name="倒角权重",
        description="设置选中边的倒角权重（直接覆盖）",
        min=0.0,
        max=4.0,
        default=1.0,
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == "MESH" and obj.mode == "EDIT"

    def execute(self, context):
        obj = context.object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        layer = bm.edges.layers.float.get("BevelWeight") or bm.edges.layers.float.new("BevelWeight")
        sel_edges = [e for e in bm.edges if e.select]

        if not sel_edges:
            self.report({'WARNING'}, "未选择任何边")
            return {'CANCELLED'}

        for e in sel_edges:
            e[layer] = self.weight

        bmesh.update_edit_mesh(me, destructive=True)
        self.report({'INFO'}, f"已设置 {len(sel_edges)} 条边的倒角权重 = {self.weight}")
        return {'FINISHED'}


class VIEW3D_PT_bevel_weight_panel(bpy.types.Panel):
    """编辑模式面板"""
    bl_label = "倒角权重快速设置"
    bl_idname = "VIEW3D_PT_bevel_weight_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "建模辅助"
    bl_context = "mesh_edit"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        layout.prop(scn, "bw_value", slider=True)
        op = layout.operator("mesh.set_bevel_weight_edit", text="应用倒角权重")
        op.weight = scn.bw_value


# ---------------------------------------------------------
# 对象模式：一键精简 & 一键法线加权
# ---------------------------------------------------------
class OBJECT_OT_add_decimate_modifier(bpy.types.Operator):
    """为所选对象添加精简修改器"""
    bl_idname = "object.add_decimate_modifier"
    bl_label = "一键精简"
    bl_options = {'REGISTER', 'UNDO'}

    ratio: bpy.props.FloatProperty(
        name="精简比率",
        description="Decimate 修改器比率",
        min=0.0,
        max=1.0,
        default=0.1,
    )

    def execute(self, context):
        selected_objs = context.selected_editable_objects
        if not selected_objs:
            self.report({'WARNING'}, "未选择任何对象")
            return {'CANCELLED'}

        for obj in selected_objs:
            if obj.type != 'MESH':
                continue
            dec = obj.modifiers.new(name="QuickDecimate", type='DECIMATE')
            dec.ratio = self.ratio
            #dec.triangulate = True  # 等价于勾上三角面化

        self.report({'INFO'}, f"已为 {len(selected_objs)} 个对象添加精简修改器")
        return {'FINISHED'}


class OBJECT_OT_add_weighted_normal(bpy.types.Operator):
    """为所选对象添加加权法线修改器"""
    bl_idname = "object.add_weighted_normal"
    bl_label = "一键法线加权"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objs = context.selected_editable_objects
        if not selected_objs:
            self.report({'WARNING'}, "未选择任何对象")
            return {'CANCELLED'}

        for obj in selected_objs:
            if obj.type != 'MESH':
                continue
            wn = obj.modifiers.new(name="WeightedNormal_Auto", type='WEIGHTED_NORMAL')
            wn.mode = 'FACE_AREA_WITH_ANGLE'
            wn.keep_sharp = True
            #obj.data.use_auto_smooth = True

        self.report({'INFO'}, f"已为 {len(selected_objs)} 个对象添加法线加权修改器")
        return {'FINISHED'}


class VIEW3D_PT_modeling_assist_panel(bpy.types.Panel):
    """对象模式面板"""
    bl_label = "建模辅助大师"
    bl_idname = "VIEW3D_PT_modeling_assist_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "建模辅助"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        col = layout.column(align=True)
        col.label(text="对象模式操作：")
        col.prop(scn, "decimate_ratio", slider=True)
        col.operator("object.add_decimate_modifier", text="一键精简").ratio = scn.decimate_ratio
        layout.separator()
        layout.operator("object.add_weighted_normal", text="一键法线加权")


# ---------------------------------------------------------
# 注册
# ---------------------------------------------------------
classes = (
    MESH_OT_set_bevel_weight_edit,
    VIEW3D_PT_bevel_weight_panel,
    OBJECT_OT_add_decimate_modifier,
    OBJECT_OT_add_weighted_normal,
    VIEW3D_PT_modeling_assist_panel,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.bw_value = bpy.props.FloatProperty(
        name="倒角权重",
        min=0.0, max=4.0, default=1.0,
        description="倒角权重"
    )
    bpy.types.Scene.decimate_ratio = bpy.props.FloatProperty(
        name="精简比率",
        min=0.0, max=1.0, default=0.1,
        description="Decimate 比率"
    )


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    del bpy.types.Scene.bw_value
    del bpy.types.Scene.decimate_ratio


if __name__ == "__main__":
    register()
