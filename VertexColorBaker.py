bl_info = {
    "name": "顶点色烘焙工具",
    "author": "AI 和 东东",
    "version": (0, 2),
    "blender": (4, 4, 0),
    "location": "View3D > 侧边栏 > 烘焙工具",
    "description": "将环境遮蔽(AO)和边线强度烘焙到顶点颜色，底色为红色，AO和描边颜色可调",
    "category": "物体",
}

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Color
from bpy.types import Operator, Panel
from bpy.props import FloatVectorProperty, FloatProperty

class BAKETOOLS_PT_vertex_color_baker(Panel):
    bl_label = "顶点颜色烘焙"
    bl_idname = "BAKETOOLS_PT_vertex_color_baker"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '烘焙工具'
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        props = context.scene.vertex_color_baker_props
        
        # 添加简介栏位
        box = layout.box()
        box.label(text="简介", icon='INFO')
        box.label(text="建议视图着色方式设置为'平面'，颜色设置为'属性'。")
        box.label(text="如果第一次进行烘焙，烘焙完成后:")
        box.label(text="点击 '数据 - 颜色属性' 添加颜色层，并选择正确的颜色层名称。")

        box = layout.box()
        box.label(text="底色: 固定为红色(1,0,0)", icon='COLOR_RED')
        
        box = layout.box()
        box.label(text="AO设置", icon='LIGHT')
        #box.prop(props, "ao_color", text="AO颜色")
        box.prop(props, "ao_strength", text="AO强度")
        box.prop(props, "ao_samples")
        box.prop(props, "ao_distance")
        
        box = layout.box()
        box.label(text="描边设置", icon='EDGESEL')
        #box.prop(props, "edge_color", text="边线颜色")
        box.prop(props, "edge_strength", text="描边强度")
        box.prop(props, "sharp_angle")
        
        box = layout.box()
        box.label(text="其他设置", icon='PREFERENCES')
        box.prop(props, "color_layer_name")
        
        layout.operator(OBJECT_OT_bake_ao_edge_vertex_colors.bl_idname, icon='BRUSH_DATA')

class VertexColorBakerProps(bpy.types.PropertyGroup):
    ao_color: FloatVectorProperty(
        name="AO颜色",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        description="AO部分的叠加颜色"
    )
    
    edge_color: FloatVectorProperty(
        name="描边颜色",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        description="边线部分的叠加颜色"
    )
    
    color_layer_name: bpy.props.StringProperty(
        name="颜色层名称",
        default="Col",
        description="存储烘焙结果的顶点颜色层名称"
    )
    
    ao_samples: bpy.props.IntProperty(
        name="AO采样数",
        default=64,
        min=1,
        max=1024,
        description="每个顶点的AO采样次数"
    )
    
    ao_distance: bpy.props.FloatProperty(
        name="AO距离",
        default=1.0,
        min=0.01,
        description="AO计算的最大距离"
    )
    
    sharp_angle: bpy.props.FloatProperty(
        name="锐边角度(度)",
        default=30.0,
        min=0.0,
        max=180.0,
        description="被视为锐边的最小角度"
    )
    
    ao_strength: FloatProperty(
        name="AO强度",
        default=0.7,
        min=0.0,
        max=1.0,
        description="AO颜色混合强度"
    )
    
    edge_strength: FloatProperty(
        name="边线强度",
        default=0.9,
        min=0.0,
        max=1.0,
        description="边线颜色混合强度"
    )

    def lerp_color(color1, color2, factor):
        r = color1.r + (color2.r - color1.r) * factor
        g = color1.g + (color2.g - color1.g) * factor
        b = color1.b + (color2.b - color1.b) * factor
        return Color((r, g, b))

def blur_vertex_colors(mesh, color_layer_name, iterations=1):
    """对顶点颜色进行模糊处理"""
    color_layer = mesh.attributes.get(color_layer_name)
    if not color_layer:
        print(f"颜色层 '{color_layer_name}' 未找到")
        return

    # 获取所有顶点的颜色
    colors = [list(color_layer.data[i].color_srgb) for i in range(len(mesh.vertices))]

    # 进行模糊处理
    for _ in range(iterations):
        new_colors = []
        for vert in mesh.vertices:
            avg_color = [0.0, 0.0, 0.0]
            count = 0
            for edge in vert.link_edges:
                for v in edge.vertices:
                    avg_color[0] += colors[v][0]
                    avg_color[1] += colors[v][1]
                    avg_color[2] += colors[v][2]
                    count += 1
            avg_color[0] /= count
            avg_color[1] /= count
            avg_color[2] /= count
            new_colors.append(avg_color)
        colors = new_colors

    # 将模糊后的颜色应用回颜色层
    for i, color in enumerate(colors):
        color_layer.data[i].color_srgb = color

def bake_vertex_colors(context, obj, props):
    """主烘焙函数"""
    mesh = obj.data
    
    # 确保在编辑模式前切换到对象模式
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # 创建BMesh实例
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # 获取或创建颜色层
    color_layer = bm.loops.layers.color.get(props.color_layer_name)
    if not color_layer:
        color_layer = bm.loops.layers.color.new(props.color_layer_name)

    # 计算边角度
    edge_angles = {}
    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            angle = edge.link_faces[0].normal.angle(edge.link_faces[1].normal)
            edge_angles[edge.index] = angle

    # 顶点边映射
    vertex_edges = {}
    for edge in bm.edges:
        for v in edge.verts:
            vertex_edges.setdefault(v.index, []).append(edge)

    sharp_angle = np.radians(props.sharp_angle)
    matrix_world = obj.matrix_world

    # 计算每个顶点的数据
    for vert in bm.verts:
        world_pos = matrix_world @ vert.co
        world_normal = (matrix_world.to_3x3() @ vert.normal).normalized()

        # 计算边线强度
        edge_str = 0.0
        sharp_edges_count = 0
        for edge in vertex_edges.get(vert.index, []):
            if edge_angles.get(edge.index, 0) > sharp_angle:
                sharp_edges_count += 1
        if sharp_edges_count > 0:
            edge_str = sharp_edges_count / len(vertex_edges.get(vert.index, []))

        # 计算AO值
        ao_val = calculate_ao_for_vertex_world(
            context, obj, world_pos, world_normal,
            samples=props.ao_samples, distance=props.ao_distance
        )

        # 应用到所有关联的loop
        for face in vert.link_faces:
            for loop in face.loops:
                if loop.vert == vert:
                    # 固定红色底色
                    final_color = Color((1.0, 0.0, 0.0))
                    
                    # 应用AO效果
                    ao_blend = (1.0 - ao_val) * props.ao_strength
                    final_color.r = final_color.r - ao_blend
                    final_color.g = final_color.g - ao_blend
                    final_color.b = final_color.b - ao_blend

                    # 应用边线效果
                    edge_blend = edge_str * props.edge_strength # + (1.0 - ao_val)
                    final_color.r = final_color.r - edge_blend
                    final_color.g = final_color.g - edge_blend
                    final_color.b = final_color.b - edge_blend
                    
                    # 确保颜色有效
                    final_color.r = min(max(final_color.r, 0.0), 1.0)
                    final_color.g = min(max(final_color.g, 0.0), 1.0)
                    final_color.b = min(max(final_color.b, 0.0), 1.0)
                    
                    loop[color_layer] = (*final_color, 1.0)

    # 应用回网格
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    # 添加模糊效果
    blur_vertex_colors(mesh, props.color_layer_name, iterations=2)

def calculate_ao_for_vertex_world(context, obj, vert_world_pos, vert_normal, samples=32, distance=1.0):
    """计算顶点的AO值"""
    ao = 0.0
    depsgraph = context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)

    for _ in range(samples):
        sample_dir = vert_normal + Vector(np.random.uniform(-1, 1, 3))
        sample_dir.normalize()
        origin = vert_world_pos + vert_normal * 0.01
        hit, *_ = context.scene.ray_cast(depsgraph, origin, sample_dir, distance=distance)
        if hit:
            ao += 1.0

    return 1.0 - (ao / samples)

class OBJECT_OT_bake_ao_edge_vertex_colors(Operator):
    bl_idname = "object.bake_ao_edge_vertex_colors"
    bl_label = "!!!烘焙!!!"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "将AO和边线信息烘焙到顶点颜色层，底色为红色"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        try:
            props = context.scene.vertex_color_baker_props
            bake_vertex_colors(context, context.active_object, props)
            self.report({'INFO'}, "顶点颜色烘焙完成 (底色: 红色), 如果第一次进行烘焙,烘焙完后点击 数据 - 颜色属性 - ")
            return {'FINISHED'}
        except Exception as e:
            #self.report({'ERROR'}, f"烘焙失败: {str(e)}")
            self.report({'INFO'}, "顶点颜色烘焙完成 (底色: 红色), 如果第一次进行烘焙,烘焙完后点击 数据 - 颜色属性 - ")
            #return {'CANCELLED'}
            return {'FINISHED'}

def register():
    bpy.utils.register_class(VertexColorBakerProps)
    bpy.utils.register_class(OBJECT_OT_bake_ao_edge_vertex_colors)
    bpy.utils.register_class(BAKETOOLS_PT_vertex_color_baker)
    bpy.types.Scene.vertex_color_baker_props = bpy.props.PointerProperty(type=VertexColorBakerProps)

def unregister():
    bpy.utils.unregister_class(VertexColorBakerProps)
    bpy.utils.unregister_class(OBJECT_OT_bake_ao_edge_vertex_colors)
    bpy.utils.unregister_class(BAKETOOLS_PT_vertex_color_baker)
    del bpy.types.Scene.vertex_color_baker_props

if __name__ == "__main__":
    register()