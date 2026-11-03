import bpy

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
        self.scene_markers = {}

    def _collect_animation_ranges(self, blender_scene):
        animation_ranges = {}

        def register_animation(animation_name, frame_start, frame_end):
            if animation_name in animation_ranges:
                old_start, old_end = animation_ranges[animation_name]
                animation_ranges[animation_name] = (min(old_start, frame_start), max(old_end, frame_end))
            else:
                animation_ranges[animation_name] = (frame_start, frame_end)

        scene_animation = blender_scene.animation_data
        if scene_animation is not None and scene_animation.action is not None:
            frame_start, frame_end = scene_animation.action.frame_range
            register_animation(scene_animation.action.name, frame_start, frame_end)

        for obj in blender_scene.objects:
            object_animation = obj.animation_data
            if object_animation is None:
                continue

            if object_animation.action is not None:
                frame_start, frame_end = object_animation.action.frame_range
                register_animation(object_animation.action.name, frame_start, frame_end)

            if object_animation.nla_tracks is None:
                continue

            for track in object_animation.nla_tracks:
                if track.mute:
                    continue
                for strip in track.strips:
                    if strip.mute or strip.action is None:
                        continue
                    register_animation(strip.action.name, strip.frame_start, strip.frame_end)

        return animation_ranges


    def gather_camera_hook(self, gltf2_camera, blender_camera, export_settings):
        self.cameras[blender_camera.name] = gltf2_camera
        if blender_camera.sensor_fit == 'AUTO':
            if gltf2_camera.extras is None:
                gltf2_camera.extras = {}
            gltf2_camera.extras['autoAspect'] = True

    def gather_scene_hook(self, gltf2_scene, blender_scene, export_settings):
        if not self.properties.enabled:
            return

        markers = blender_scene.timeline_markers
        extMarkers = []
        fps = blender_scene.render.fps
        animation_ranges = self._collect_animation_ranges(blender_scene)
        for marker in markers:
            markerData = {'name': marker.name,'frame': marker.frame, 'time': 1.0 * marker.frame / fps}
            if marker.camera is not None:
                camIndex = self.cameras[marker.camera.data.name]
                if camIndex is not None:
                    markerData['camera'] = camIndex

            marker_animations = []
            for animation_name, frame_range in animation_ranges.items():
                frame_start, frame_end = frame_range
                if frame_start <= marker.frame <= frame_end:
                    marker_animations.append(animation_name)

            if len(marker_animations) == 0:
                extMarkers.append(markerData)
                continue

            for animation_name in marker_animations:
                marker_entry = dict(markerData)
                marker_entry['animation'] = animation_name
                extMarkers.append(marker_entry)

        self.cameras.clear()

        self.scene_markers[id(gltf2_scene)] = extMarkers
        if gltf2_scene.name:
            self.scene_markers[gltf2_scene.name] = extMarkers

    def gather_gltf_extensions_hook(self, gltf2_asset, export_settings):
        if not self.properties.enabled:
            return

        if gltf2_asset is None or gltf2_asset.scenes is None or len(gltf2_asset.scenes) == 0:
            self.scene_markers.clear()
            return

        active_scene_index = gltf2_asset.scene if gltf2_asset.scene is not None else 0
        if active_scene_index < 0 or active_scene_index >= len(gltf2_asset.scenes):
            active_scene_index = 0

        active_scene = gltf2_asset.scenes[active_scene_index]

        extension_payload = self.scene_markers.get(id(active_scene))
        if extension_payload is None and active_scene.name:
            extension_payload = self.scene_markers.get(active_scene.name)

        if extension_payload is None:
            self.scene_markers.clear()
            return

        if gltf2_asset.extensions is None:
            gltf2_asset.extensions = {}

        gltf2_asset.extensions[self.properties.extension_name] = self.Extension(
            name=self.properties.extension_name,
            extension={'markers': extension_payload},
            required=extension_is_required)

        self.scene_markers.clear()


def dump(obj):
    for attr in dir(obj):
        if hasattr( obj, attr ):
            print( "obj.%s = %s" % (attr, getattr(obj, attr)))
