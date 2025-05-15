# from mathutils.bvhtree import BVHTree  # BVH
from bpy.props import FloatVectorProperty, FloatProperty
from bpy.types import Operator, Panel
from mathutils import Vector, Color
import numpy as np
import bmesh
import bpy


bl_info = {
    "name": "顶点色烘焙工具",
    "author": "东东",
    "version": (0, 31),
    "blender": (4, 0, 0),
    "location": "View3D > 侧边栏 > 顶点色烘焙工具",
    "description": "将环境遮蔽（AO）和描边烘焙到顶点色的工具",
    "category": "Object",
    "doc_url": "https://github.com/LiuSong0413/VertexColorBaker", 
    #"support": "TESTING", 
}


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

        # 版本建议
        #box = layout.box()
        # box.label(text="版本建议： 4.0 +", icon='INFO')
        # 添加简介栏位
        box = layout.box()
        box.label(text="提示", icon='INFO')
        # box.label(text="着色方式--平面，颜色设置--属性")
        box.label(text="第一次进行烘焙完成后:")
        box.label(text="点击 '数据 - 颜色属性' ，选择正确的颜色层")

        box = layout.box()
        box.label(text="底色: 固定为红色(1,0,0)", icon='COLOR_RED')

        layout.separator()

        box = layout.box()
        box.label(text="AO设置", icon='LIGHT')
        box.prop(props, "ao_strength", text="AO强度")
        box.prop(props, "ao_samples")
        box.prop(props, "ao_distance")

        box = layout.box()
        box.label(text="描边设置", icon='EDGESEL')
        box.prop(props, "edge_strength", text="描边强度")
        box.prop(props, "sharp_angle")

        box = layout.box()
        box.label(text="其他设置", icon='SETTINGS')
        box.prop(props, "color_layer_name")
        box.prop(props, "autoJump")

        layout.operator(
            OBJECT_OT_bake_ao_edge_vertex_colors.bl_idname, icon='BRUSH_DATA')

        layout.separator()
        layout.operator("object.convert_vertex_color_blackwhite",
                        icon='IMAGE_RGB_ALPHA')


class VertexColorBakerProps(bpy.types.PropertyGroup):

    color_layer_name: bpy.props.StringProperty(
        name="颜色层名称",
        default="Col",
        description="存储烘焙结果的顶点颜色层名称"
    )
    
    autoJump: bpy.props.BoolProperty(
        name="烘焙后自动切换显示模式？",
        default=False,
        description="关闭后，不会在烘焙之后自动切换光照 -- '平面' ， 颜色 -- '属性'"
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
        max=10.0,
        description="AO颜色混合强度"
    )

    edge_strength: FloatProperty(
        name="边线强度",
        default=0.9,
        min=0.0,
        max=10.0,
        description="边线颜色混合强度"
    )

    def lerp_color(color1, color2, factor):
        r = color1.r + (color2.r - color1.r) * factor
        g = color1.g + (color2.g - color1.g) * factor
        b = color1.b + (color2.b - color1.b) * factor
        return Color((r, g, b))

# region  "对顶点颜色进行模糊处理"
# def blur_vertex_colors(mesh, color_layer_name, iterations=1):
#
#     color_layer = mesh.attributes.get(color_layer_name)
#     if not color_layer:
#         print(f"颜色层 '{color_layer_name}' 未找到")
#         return

#     # 获取所有顶点的颜色
#     colors = [list(color_layer.data[i].color_srgb)
#               for i in range(len(mesh.vertices))]

#     # 进行模糊处理
#     for _ in range(iterations):
#         new_colors = []
#         for vert in mesh.vertices:
#             avg_color = [0.0, 0.0, 0.0]
#             count = 0
#             for edge in vert.link_edges:
#                 for v in edge.vertices:
#                     avg_color[0] += colors[v][0]
#                     avg_color[1] += colors[v][1]
#                     avg_color[2] += colors[v][2]
#                     count += 1
#             avg_color[0] /= count
#             avg_color[1] /= count
#             avg_color[2] /= count
#             new_colors.append(avg_color)
#         colors = new_colors

#     # 将模糊后的颜色应用回颜色层
#     for i, color in enumerate(colors):
#         color_layer.data[i].color_srgb = color
# endregion


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
            try:
                angle = edge.link_faces[0].normal.angle(
                    edge.link_faces[1].normal)
                edge_angles[edge.index] = angle
            except ValueError:
                edge_angles[edge.index] = 0.0

    # 顶点边映射
    vertex_edges = {}
    for edge in bm.edges:
        for v in edge.verts:
            vertex_edges.setdefault(v.index, []).append(edge)

    sharp_angle = np.radians(props.sharp_angle)
    matrix_world = obj.matrix_world

    # 获取总顶点数（在循环前计算）
    total_vertices = len(bm.verts)
    
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
            edge_str = sharp_edges_count / \
                len(vertex_edges.get(vert.index, []))

        # 计算AO值
        ao_val = calculate_ao_for_vertex_world(
            context, obj, world_pos, world_normal,
            samples=props.ao_samples, 
            distance=props.ao_distance,
            vertex_index=vert.index,  # Pass the index number instead of the BMVert object
            total_vertices=total_vertices
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
                    edge_blend = edge_str * \
                        props.edge_strength  # + (1.0 - ao_val)
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

    print(f"\n烘焙结束")
    # 添加模糊效果
    # blur_vertex_colors(mesh, props.color_layer_name, iterations=props.blurIerations)


def calculate_ao_for_vertex_world(context, obj, vert_world_pos, vert_normal, 
                                samples=32, distance=1.0, 
                                vertex_index=0, total_vertices=1):
    ao = 0.0
    depsgraph = context.evaluated_depsgraph_get()
    #obj_eval = obj.evaluated_get(depsgraph)
    
    # 初始化进度（存储到 window_manager）
    if vertex_index == 0:
        context.window_manager.progress_begin(0, 100)  # 替代 bpy.ops.wm.progress_begin

    for i in range(samples):
        sample_dir = vert_normal + Vector(np.random.uniform(-1, 1, 3))
        sample_dir.normalize()
        origin = vert_world_pos + vert_normal * 0.01
        hit, *_ = context.scene.ray_cast(depsgraph, origin, sample_dir, distance=distance)
        if hit:
            ao += 1.0
            
    # 只在每个顶点完成后更新一次进度（避免频繁更新）
    vertex_progress = (vertex_index + 1) / total_vertices * 100  # +1 确保从 1% 开始
    vertex_progress_int = int(vertex_progress)  # 转为整数（直接截断小数部分）
    print(f"整体烘焙进度: {vertex_progress_int}%", end="\r")
    #vertex_progress = min(100, vertex_progress)  # 确保不超过 100%
    context.window_manager.progress_update(vertex_progress_int)

    # 仅在最后一个顶点完成时结束进度条
    if vertex_index == total_vertices - 1:
        context.window_manager.progress_end()
    
    return 1.0 - (ao / samples)

class OBJECT_OT_bake_ao_edge_vertex_colors(Operator):
    bl_idname = "object.bake_ao_edge_vertex_colors"
    bl_label = "!!!烘焙!!!"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "将AO和描边信息烘焙到顶点色"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        
        props = context.scene.vertex_color_baker_props
        # 获取3D视图并设置着色模式
        if props.autoJump:
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.shading.light = 'FLAT'
                            space.shading.color_type = 'VERTEX'

        try:
            bake_vertex_colors(context, context.active_object, props)
            
            self.report({'INFO'}, "烘焙完成!!查找颜色属性")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"报错: {str(e)}")
            # self.report({'INFO'}, "顶点颜色烘焙完成 (底色: 红色), 如果第一次进行烘焙,烘焙完后点击 数据 - 颜色属性 - ")
            return {'CANCELLED'}
            # return {'FINISHED'}


class OBJECT_OT_convert_vertex_color_blackwhite(Operator):
    bl_idname = "object.convert_vertex_color_blackwhite"
    bl_label = "顶点色黑白切换"
    bl_description = "将当前顶点颜色转换为黑白或红黑格式"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.vertex_color_baker_props

        # 强制同步数据到对象模式
        if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            # 关键修改1：使用BMesh确保获取最新颜色数据
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            color_layer = bm.loops.layers.color.get(props.color_layer_name)

            if not color_layer:
                self.report({'WARNING'}, f"找不到颜色层: {props.color_layer_name}")
                bm.free()
                continue

            # 关键修改2：全新的智能颜色转换逻辑
            is_red_black = True  # 先检测当前模式

            for face in bm.faces:
                for loop in face.loops:
                    r, g, b = loop[color_layer][0], loop[color_layer][1], loop[color_layer][2]
                    if g > 0.01 or b > 0.01:  # 如果发现非红黑色
                        is_red_black = False
                        break
                if not is_red_black:
                    break

            # 执行转换
            for face in bm.faces:
                for loop in face.loops:
                    if is_red_black:
                        # 红黑→灰度：取红色通道作为灰度值
                        gray = loop[color_layer][0]
                        loop[color_layer] = (gray, gray, gray, 1.0)
                    else:
                        # 灰度→红黑：取亮度作为红色通道
                        r, g, b = loop[color_layer][0], loop[color_layer][1], loop[color_layer][2]
                        # 使用更精确的亮度转换（CIE标准）
                        brightness = 0.299 * r + 0.587 * g + 0.114 * b
                        loop[color_layer] = (brightness, 0.0, 0.0, 1.0)

            # 关键修改3：确保数据写回
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()  # 强制更新显示

        self.report({'INFO'}, f"已转换为{'灰度' if is_red_black else '红黑'}模式")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(VertexColorBakerProps)
    bpy.utils.register_class(OBJECT_OT_convert_vertex_color_blackwhite)
    bpy.utils.register_class(OBJECT_OT_bake_ao_edge_vertex_colors)
    bpy.utils.register_class(BAKETOOLS_PT_vertex_color_baker)
    bpy.types.Scene.vertex_color_baker_props = bpy.props.PointerProperty(
        type=VertexColorBakerProps)


def unregister():
    bpy.utils.unregister_class(VertexColorBakerProps)
    bpy.utils.register_class(OBJECT_OT_convert_vertex_color_blackwhite)
    bpy.utils.unregister_class(OBJECT_OT_bake_ao_edge_vertex_colors)
    bpy.utils.unregister_class(BAKETOOLS_PT_vertex_color_baker)
    del bpy.types.Scene.vertex_color_baker_props


if __name__ == "__main__":
    register()
