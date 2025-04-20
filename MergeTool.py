import bpy
import bmesh
import math

bl_info = {
    "name": "合一体优化工具",
    "author": "东东",
    "version": (0, 3),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Edit Tab",
    "description": "布尔运算交叉区域优化工具，\n包含边缘检测、顶点合并和复杂面查找功能",
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

class BooleanEdgeDetector(bpy.types.Operator):
    """仅检测布尔运算交叉区域"""
    bl_idname = "mesh.boolean_edge_detector"
    bl_label = "查找区域"
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

        selected_edges = self.select_boolean_edges(bm, props.edge_threshold)
        if not selected_edges:
            self.report({'WARNING'}, "未检测到符合角度的边缘")
            return {'CANCELLED'}

        bpy.ops.mesh.select_all(action='DESELECT')
        for edge in selected_edges:
            edge.select = True
            for vert in edge.verts:
                vert.select = True
        
        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, f"找到 {len(selected_edges)} 条布尔交界边")
        return {'FINISHED'}

    def select_boolean_edges(self, bm, angle_threshold):
        selected_edges = []
        angle_threshold_rad = math.radians(angle_threshold)
        
        for edge in bm.edges:
            if len(edge.link_faces) == 2 and not edge.is_boundary:
                face1, face2 = edge.link_faces
                angle = face1.normal.angle(face2.normal)
                if angle > angle_threshold_rad:
                    selected_edges.append(edge)
        
        return selected_edges

class BooleanEdgeOptimizer(bpy.types.Operator):
    """优化当前选中区域的顶点，按照合并距离进行合并"""
    bl_idname = "mesh.boolean_edge_optimizer"
    bl_label = "合并选中区域相邻点"
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

        selected_verts = [v for v in bm.verts if v.select]
        if not selected_verts:
            self.report({'WARNING'}, "没有选中的顶点")
            return {'CANCELLED'}

        verts_to_merge = set(selected_verts)

        bpy.ops.mesh.select_all(action='DESELECT')
        for face in bm.faces:
            face.select = any(v in verts_to_merge for v in face.verts)
        bmesh.update_edit_mesh(me)

        bpy.ops.mesh.dissolve_limited(angle_limit=0.01, use_dissolve_boundaries=False)

        bpy.ops.mesh.select_all(action='DESELECT')
        for v in verts_to_merge:
            v.select = True
        bmesh.update_edit_mesh(me)
        bpy.ops.mesh.remove_doubles(threshold=props.merge_distance)

        bpy.ops.mesh.select_all(action='DESELECT')
        bmesh.update_edit_mesh(me)

        self.report({'INFO'}, f"优化完成！合并了 {len(verts_to_merge)} 个顶点")
        return {'FINISHED'}

class FindComplexFaces(bpy.types.Operator):
    """选中所有顶点数大于4的面（五边形及以上）"""
    bl_idname = "mesh.find_complex_faces"
    bl_label = "优化复杂面"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object

        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "请选择一个网格物体")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        
        complex_faces = [face for face in bm.faces if len(face.verts) > 4]

        bpy.ops.mesh.select_all(action='DESELECT')
        for face in complex_faces:
            face.select = True
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        bpy.ops.mesh.tris_convert_to_quads()


        bmesh.update_edit_mesh(me)
        
        if complex_faces:
            self.report({'INFO'}, f"找到 {len(complex_faces)} 个五边形及以上面")
        else:
            self.report({'WARNING'}, "未检测到五边形及以上面")
        
        return {'FINISHED'}

class BooleanEdgeOptimizerPanel(bpy.types.Panel):
    """合一体优化面板"""
    bl_label = "合一体优化工具"
    bl_idname = "OBJECT_PT_boolean_edge_optimizer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "合一体优化"
    bl_context = "mesh_edit"

    def draw(self, context):
        layout = self.layout
        props = context.scene.boolean_edge_optimizer_props

        box = layout.box()
        box.label(text="边缘检测设置:", icon='EDGESEL')
        box.prop(props, "edge_threshold")
        box.operator("mesh.boolean_edge_detector", icon='VIEWZOOM')

        box = layout.box()
        box.label(text="顶点合并设置:", icon='AUTOMERGE_ON')
        box.prop(props, "merge_distance")
        box.operator("mesh.boolean_edge_optimizer", icon='VERTEXSEL')

        box = layout.box()
        box.label(text="面复杂度检测:", icon='MESH_DATA')
        box.operator("mesh.find_complex_faces", icon='UV_FACESEL')

classes = (
    BooleanEdgeOptimizerProperties,
    BooleanEdgeDetector,
    BooleanEdgeOptimizer,
    FindComplexFaces,
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
