import bpy
import io_scene_gltf2.io.com.gltf2_io
from io_scene_gltf2.blender.exp.gltf2_blender_gather_cameras import gather_camera
from io_scene_gltf2.blender.exp import gltf2_blender_get
from io_scene_gltf2.blender.exp import gltf2_blender_gather_texture_info
from io_scene_gltf2.blender.exp import gltf2_blender_search_node_tree

bl_info = {
    "name": "Timeline markers Extension",
    "extension_name": "WEBGI_animation_markers",
    "category": "GLTF Exporter",
    "version": (1, 0, 0),
    "blender": (2, 92, 0),
    'location': 'File > Export > glTF 2.0',
    'description': 'Extension to export timeline markers and cameras in gltf.',
    'tracker_url': '',  # Replace with your issue tracker
    'isDraft': False,
    'developer': "Palash Bansal",
    'url': 'https://repalash.com',
}

# https://github.com/KhronosGroup/glTF-Blender-IO/tree/master/example-addons/example_gltf_extension

# glTF extensions are named following a convention with known prefixes.
# See: https://github.com/KhronosGroup/glTF/tree/master/extensions#about-gltf-extensions
# also: https://github.com/KhronosGroup/glTF/blob/master/extensions/Prefixes.md

extension_is_required = False


class TimelineMarkersExtensionProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name=bl_info["name"],
        description='Include this extension in the exported glTF file.',
        default=True
    )
    extension_name: bpy.props.StringProperty(
        name="Extension",
        description='GLTF extension name.',
        default=bl_info["extension_name"]
    )

def register():
    bpy.utils.register_class(TimelineMarkersExtensionProperties)
    bpy.types.Scene.TimelineMarkersExtensionProperties = bpy.props.PointerProperty(type=TimelineMarkersExtensionProperties)

def register_panel():
    try:
        bpy.utils.register_class(GLTF_PT_TimelineMarkersExtensionPanel)
    except Exception:
        pass

def unregister_panel():
    try:
        bpy.utils.unregister_class(GLTF_PT_TimelineMarkersExtensionPanel)
    except Exception:
        pass

def unregister():
    unregister_panel()
    bpy.utils.unregister_class(TimelineMarkersExtensionProperties)
    del bpy.types.Scene.TimelineMarkersExtensionProperties


class GLTF_PT_TimelineMarkersExtensionPanel(bpy.types.Panel):

    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Enabled"
    bl_parent_id = "GLTF_PT_export_user_extensions"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        props = bpy.context.scene.TimelineMarkersExtensionProperties
        self.layout.prop(props, 'enabled')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        props = bpy.context.scene.TimelineMarkersExtensionProperties
        layout.active = props.enabled

        box = layout.box()
        box.label(text=props.extension_name)

        layout.prop(props, 'extension_name', text="GLTF extension name")


class glTF2ExportUserExtension:

    def __init__(self):
        # We need to wait until we create the gltf2TimelineMarkersExtension to import the gltf2 modules
        # Otherwise, it may fail because the gltf2 may not be loaded yet
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension
        self.properties = bpy.context.scene.TimelineMarkersExtensionProperties
        self.cameras = {}


    def gather_camera_hook(self, gltf2_camera: io_scene_gltf2.io.com.gltf2_io.Camera, blender_camera: bpy.types.Camera, export_settings):
        self.cameras[blender_camera.name] = gltf2_camera
        if blender_camera.sensor_fit == 'AUTO':
            if gltf2_camera.extras is None:
                gltf2_camera.extras = {}
            gltf2_camera.extras['autoAspect'] = True

    def gather_scene_hook(self, gltf2_scene: io_scene_gltf2.io.com.gltf2_io.Scene, blender_scene: bpy.types.Scene, export_settings):
        markers = blender_scene.timeline_markers
        extMarkers = []
        for marker in markers:
            markerData = {'name': marker.name,'frame': marker.frame}
            if marker.camera is not None:
                camIndex = self.cameras[marker.camera.data.name]
                if camIndex is not None:
                    markerData['camera'] = camIndex
            extMarkers.append(markerData)

        self.cameras.clear()

        gltf2_scene.extensions[self.properties.extension_name] = self.Extension(
            name=self.properties.extension_name,
            extension={'markers': extMarkers},
            required=extension_is_required)


def dump(obj):
    for attr in dir(obj):
        if hasattr( obj, attr ):
            print( "obj.%s = %s" % (attr, getattr(obj, attr)))
