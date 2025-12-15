bl_info = {
    "name": "Bevel Weight Quick Setter (Edit Mode, Blender 4.5)",
    "author": "Your Name",
    "version": (1, 5),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Bevel Tab",
    "description": "Set bevel weights on selected edges in Edit Mode via transform operator",
    "category": "Mesh",
}

import bpy


class MESH_OT_set_bevel_weight_edit(bpy.types.Operator):
    """Set Bevel Weight using built-in transform operator"""
    bl_idname = "mesh.set_bevel_weight_edit"
    bl_label = "Apply Bevel Weight"
    bl_options = {'REGISTER', 'UNDO'}

    weight: bpy.props.FloatProperty(
        name="Bevel Weight",
        description="Bevel weight value to apply",
        min=-1.0, max=4.0,
        default=1.0,
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == "MESH" and obj.mode == "EDIT"

    def execute(self, context):
        # 调用 Blender 内置 operator，保证界面和数据都同步
        bpy.ops.transform.edge_bevelweight(value=self.weight, snap=False)
        self.report({'INFO'}, f"Applied Edge Bevel Weight = {self.weight}")
        return {'FINISHED'}


class VIEW3D_PT_bevel_weight_panel(bpy.types.Panel):
    """Panel in N-sidebar"""
    bl_label = "Bevel Weight Setter"
    bl_idname = "VIEW3D_PT_bevel_weight_setter"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Bevel"
    bl_context = "mesh_edit"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "bw_value", slider=True)
        op = layout.operator("mesh.set_bevel_weight_edit", text="Apply Weight")
        op.weight = scene.bw_value


def register():
    bpy.types.Scene.bw_value = bpy.props.FloatProperty(
        name="Bevel Weight",
        min=-1.0,
        max=4.0,
        default=1.0,
        description="Bevel weight value to apply to selected edges"
    )
    bpy.utils.register_class(MESH_OT_set_bevel_weight_edit)
    bpy.utils.register_class(VIEW3D_PT_bevel_weight_panel)


def unregister():
    del bpy.types.Scene.bw_value
    bpy.utils.unregister_class(VIEW3D_PT_bevel_weight_panel)
    bpy.utils.unregister_class(MESH_OT_set_bevel_weight_edit)


if __name__ == "__main__":
    register()
