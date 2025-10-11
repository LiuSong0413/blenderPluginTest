bl_info = {
    "name": "图像自动导出工具",
    "author": "Dox",
    "version": (0, 2),
    "blender": (2, 80, 0),
    "location": "Image Editor > Image > Save Copy",
    "description": "自动导出PNG和OpenEXR格式的图像副本到AutoExport文件夹",
    "category": "Image",
}

import bpy
import os

class IMAGE_OT_save_copy_png_exr(bpy.types.Operator):
    """自动导出PNG和OpenEXR格式的图像副本到AutoExport文件夹"""
    bl_idname = "image.save_copy_png_exr"
    bl_label = "PNG+EXR to AutoExport"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        # 只在图像编辑器中有活动图像时启用
        return context.space_data and context.space_data.image
    
    def execute(self, context):
        image = context.space_data.image
        
        if not image:
            self.report({'WARNING'}, "没有选中的图像")
            return {'CANCELLED'}
        
        # 获取Blender文件所在目录
        blend_file_path = bpy.data.filepath
        if not blend_file_path:
            self.report({'WARNING'}, "请先保存Blender文件")
            return {'CANCELLED'}
        
        # 创建AutoExport文件夹
        blend_dir = os.path.dirname(blend_file_path)
        auto_export_dir = os.path.join(blend_dir, "AutoExport")
        
        if not os.path.exists(auto_export_dir):
            try:
                os.makedirs(auto_export_dir)
                self.report({'INFO'}, f"创建目录: {auto_export_dir}")
            except Exception as e:
                self.report({'ERROR'}, f"无法创建目录: {str(e)}")
                return {'CANCELLED'}
        
        # 获取图像名称（不含扩展名）
        image_name = image.name
        if image.filepath_raw:
            image_name = os.path.splitext(os.path.basename(image.filepath_raw))[0]
        else:
            image_name = os.path.splitext(image_name)[0]
        
        # 保存原始渲染设置
        render_settings = context.scene.render
        original_file_format = render_settings.image_settings.file_format
        original_color_mode = render_settings.image_settings.color_mode
        original_color_depth = render_settings.image_settings.color_depth
        original_compression = render_settings.image_settings.compression
        
        # 导出PNG
        png_path = os.path.join(auto_export_dir, image_name + ".png")
        try:
            # 设置PNG格式选项
            render_settings.image_settings.file_format = 'PNG'
            render_settings.image_settings.color_mode = 'RGB'
            render_settings.image_settings.compression = 15  # 最高压缩
            # 色彩管理：跟随场景
            render_settings.image_settings.color_management = 'FOLLOW_SCENE'
            
            # 保存PNG
            image.save_render(png_path, scene=context.scene)
            self.report({'INFO'}, f"PNG已保存: {png_path}")
        except Exception as e:
            self.report({'ERROR'}, f"保存PNG失败: {str(e)}")
            # 恢复原始设置
            render_settings.image_settings.file_format = original_file_format
            render_settings.image_settings.color_mode = original_color_mode
            render_settings.image_settings.color_depth = original_color_depth
            render_settings.image_settings.compression = original_compression
            return {'CANCELLED'}
        
        # 导出OpenEXR
        exr_path = os.path.join(auto_export_dir, image_name + ".exr")
        try:
            # 设置EXR格式选项
            render_settings.image_settings.file_format = 'OPEN_EXR'
            render_settings.image_settings.color_mode = 'RGB'
            render_settings.image_settings.color_depth = '16'  # 半精度浮点
            render_settings.image_settings.exr_codec = 'DWAA'  # ZIP压缩
            
            # 保存EXR
            image.save_render(exr_path, scene=context.scene)
            self.report({'INFO'}, f"EXR已保存: {exr_path}")
        except Exception as e:
            self.report({'ERROR'}, f"保存EXR失败: {str(e)}")
        
        # 恢复原始设置
        render_settings.image_settings.file_format = original_file_format
        render_settings.image_settings.color_mode = original_color_mode
        render_settings.image_settings.color_depth = original_color_depth
        render_settings.image_settings.compression = original_compression
        
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.separator()
    self.layout.operator(IMAGE_OT_save_copy_png_exr.bl_idname, text="自动导出 PNG + EXR")

def register():
    bpy.utils.register_class(IMAGE_OT_save_copy_png_exr)
    bpy.types.IMAGE_MT_image.append(menu_func)

def unregister():
    bpy.utils.unregister_class(IMAGE_OT_save_copy_png_exr)
    bpy.types.IMAGE_MT_image.remove(menu_func)

if __name__ == "__main__":
    register()