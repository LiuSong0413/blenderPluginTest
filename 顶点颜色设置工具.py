bl_info = {
    "name": "顶点颜色设置工具",
    "author": "Your Name",
    "version": (1, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > 工具",
    "description": "设置选中顶点颜色，支持自定义颜色和颜色预设",
    "category": "Mesh",
}

import bpy
from bpy.props import FloatVectorProperty, CollectionProperty, BoolProperty
from bpy.types import Operator, Panel, PropertyGroup


class VertexColorPresetItem(PropertyGroup):
    color: FloatVectorProperty(
        name="颜色",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )
    enabled: BoolProperty(
        name="启用",
        default=False
    )


class VERTEXCOLOR_OT_set_vertex_color(Operator):
    """设置选定顶点的自定义颜色"""
    bl_idname = "vertex_color.set_vertex_color"
    bl_label = "设置顶点颜色"
    bl_options = {'REGISTER', 'UNDO'}

    color: FloatVectorProperty(
        name="颜色",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'MESH' and context.object.mode == 'EDIT')

    def execute(self, context):
        if not apply_vertex_color_to_selected(self.color):
            self.report({'ERROR'}, "顶点颜色层数据为空，无法设置颜色")
            return {'CANCELLED'}
        return {'FINISHED'}


class VERTEXCOLOR_OT_apply_presets(Operator):
    """应用启用的预设颜色到选中顶点"""
    bl_idname = "vertex_color.apply_presets"
    bl_label = "应用启用的预设颜色"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'MESH' and context.object.mode == 'EDIT')

    def execute(self, context):
        scene = context.scene
        presets = scene.vertex_color_presets
        success = False
        for preset in presets:
            if preset.enabled:
                if apply_vertex_color_to_selected(preset.color):
                    success = True
        
        if not success:
            self.report({'ERROR'}, "顶点颜色层数据为空，无法设置颜色")
            return {'CANCELLED'}
        return {'FINISHED'}

def ensure_vertex_color_layer(mesh, name="Col"):
    # 确保mesh有color_attributes层，类型为FLOAT_COLOR，domain为CORNER（顶点色）
    if name not in mesh.color_attributes:
        mesh.color_attributes.new(name=name, type='FLOAT_COLOR', domain='CORNER')
    return mesh.color_attributes[name]

def apply_vertex_color_to_selected(color):
    obj = bpy.context.object
    mesh = obj.data

    color_layer = ensure_vertex_color_layer(mesh)

    # 切换到对象模式，刷新mesh数据和选中状态
    bpy.ops.object.mode_set(mode='OBJECT')

    # 强制刷新数据，避免颜色层空
    mesh.update()

    selected_verts = {v.index for v in mesh.vertices if v.select}

    bpy.ops.object.mode_set(mode='EDIT')

    if not color_layer.data:
        # 如果颜色层数据为空，强制刷新一下mesh
        print("颜色层数据为空，尝试刷新mesh数据")
        mesh.update()
        if not color_layer.data:
            # 仍然为空，返回错误或提示
            return False

    for poly in mesh.polygons:
        for loop_index in poly.loop_indices:
            loop = mesh.loops[loop_index]
            if loop.vertex_index in selected_verts:
                color_layer.data[loop_index].color = (*color[:3], 1.0)
    
    return True


class VERTEXCOLOR_PT_panel(Panel):
    """顶点颜色设置面板"""
    bl_label = "顶点颜色设置"
    bl_idname = "VERTEXCOLOR_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "工具"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.label(text="颜色预设：")
        for i, item in enumerate(scene.vertex_color_presets):
            row = layout.row(align=True)
            row.prop(item, "enabled", text="")
            row.prop(item, "color", text=f"预设 {i + 1}")

        layout.separator()
        layout.prop(scene, "vertex_color_prop", text="自定义颜色")
        layout.operator(VERTEXCOLOR_OT_set_vertex_color.bl_idname, text="应用颜色（自定义）").color = scene.vertex_color_prop
        layout.operator(VERTEXCOLOR_OT_apply_presets.bl_idname, text="应用颜色（预设）")


def init_presets_if_needed():
    scene = bpy.context.scene
    if not hasattr(scene, "vertex_color_presets"):
        return None

    presets = scene.vertex_color_presets
    if len(presets) == 0:
        for i in range(10):
            gray = i / 9.0
            item = presets.add()
            item.color = (gray, gray, gray, 1.0)
        for c in [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)]:
            item = presets.add()
            item.color = c
    return None


classes = (
    VertexColorPresetItem,
    VERTEXCOLOR_OT_set_vertex_color,
    VERTEXCOLOR_OT_apply_presets,
    VERTEXCOLOR_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.vertex_color_presets = CollectionProperty(type=VertexColorPresetItem)
    bpy.types.Scene.vertex_color_prop = FloatVectorProperty(
        name="顶点颜色",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )

    bpy.app.timers.register(init_presets_if_needed, first_interval=0.1)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.vertex_color_presets
    del bpy.types.Scene.vertex_color_prop


if __name__ == "__main__":
    register()
