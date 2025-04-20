import bpy
import bmesh

bl_info = {
    "name": "布尔交界优化工具",
    "author": "东东",
    "version": (0, 1),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Edit Tab",
    "description": "精确优化布尔运算交叉区域布线，仅优化选中区域(支持调试模式)",
    "category": "Mesh",
    "doc_url": "https://github.com/LiuSong0413/VertexColorBaker", 
    "support": "TESTING", 
}

class BooleanEdgeOptimizerProperties(bpy.types.PropertyGroup):
    edge_threshold: bpy.props.FloatProperty(
        name="边缘角度",
        description="识别交叉边缘的角度阈值(度)",
        default=45.0,
        min=0.001,
        max=180.0
    )

    merge_distance: bpy.props.FloatProperty(
        name="合并距离",
        description="近点合并的阈值",
        default=0.001,
        min=0.00001,
        max=1.0
    )

    debug_mode: bpy.props.BoolProperty(
        name="显示检测结果",
        description="仅显示检测结果，不修改网格",
        default=False
    )

class BooleanEdgeOptimizer(bpy.types.Operator):
    """优化布尔运算交叉区域布线"""
    bl_idname = "mesh.boolean_edge_optimizer"
    bl_label = "布尔交叉区布线优化(增强版)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.boolean_edge_optimizer_props
        obj = context.active_object

        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "请选择一个网格物体")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        # 检测交界边
        selected_edges = self.select_boolean_edges(bm, props.edge_threshold)
        if not selected_edges:
            self.report({'WARNING'}, "未检测到符合角度的边缘")
            return {'CANCELLED'}

        # 选中相关顶点
        verts_to_merge = set()
        for edge in selected_edges:
            verts_to_merge.update(edge.verts)

        if props.debug_mode:
            # 只选中检测到的边用于可视化反馈
            bpy.ops.mesh.select_all(action='DESELECT')
            for edge in selected_edges:
                edge.select = True
            for v in verts_to_merge:
                v.select = True
            bmesh.update_edit_mesh(me)
            self.report({'INFO'}, f"[调试] 选中 {len(selected_edges)} 条边")
            return {'FINISHED'}

        # 选择边相关的面，用于 dissolve 优化
        bpy.ops.mesh.select_all(action='DESELECT')
        for face in bm.faces:
            face.select = False
        for edge in selected_edges:
            for face in edge.link_faces:
                face.select = True
        bmesh.update_edit_mesh(me)

        # dissolve（面优化）
        bpy.ops.mesh.dissolve_limited(angle_limit=0.01, use_dissolve_boundaries=False)

        # 合并近点
        bpy.ops.mesh.select_all(action='DESELECT')
        for v in verts_to_merge:
            v.select = True
        bmesh.update_edit_mesh(me)
        bpy.ops.mesh.remove_doubles(threshold=props.merge_distance)

        # 完成
        bpy.ops.mesh.select_all(action='DESELECT')
        bmesh.update_edit_mesh(me)

        self.report({'INFO'}, f"优化完成！处理了 {len(selected_edges)} 条边")
        return {'FINISHED'}

    def select_boolean_edges(self, bm, angle_threshold):
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.edges_select_sharp(sharpness=angle_threshold)
        bmesh.update_edit_mesh(bpy.context.active_object.data)
        return [e for e in bm.edges if e.select]

class BooleanEdgeOptimizerPanel(bpy.types.Panel):
    """布尔交叉区优化面板"""
    bl_label = "布尔交界优化工具"
    bl_idname = "OBJECT_PT_boolean_edge_optimizer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "交界优化"
    bl_context = "mesh_edit"

    def draw(self, context):
        layout = self.layout
        props = context.scene.boolean_edge_optimizer_props

        box = layout.box()
        box.label(text="边缘检测设置:")
        box.prop(props, "edge_threshold")

        box = layout.box()
        box.label(text="布线优化设置:")
        box.prop(props, "merge_distance")

        layout.prop(props, "debug_mode")
        layout.operator("mesh.boolean_edge_optimizer")

classes = (
    BooleanEdgeOptimizerProperties,
    BooleanEdgeOptimizer,
    BooleanEdgeOptimizerPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.boolean_edge_optimizer_props = bpy.props.PointerProperty(
        type=BooleanEdgeOptimizerProperties
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.boolean_edge_optimizer_props

if __name__ == "__main__":
    register()
