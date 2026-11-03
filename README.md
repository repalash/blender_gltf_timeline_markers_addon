[![Blender](misc/Blender_logo.png)](http://www.blender.org/) [![glTF](misc/glTF_logo.png)](https://www.khronos.org/gltf/) [![three.js](misc/threejs_logo.png)](https://threejs.org/)

GLTF Timeline Markers extension
======================================

Custom extension to support animation timeline markers with camera binding support in GLTF/GLB.

[Blender Addon](./__init__.py)
--------------
Put this folder in the python addons directory in blender.

For Mac its `/Applications/Blender.app/Contents/Resources/<version>/scripts/addons`
For Linux `/home/<username>/.config/blender/<version>/scripts/addons`

The markers are exported at the glTF document root inside `extensions.WEBGI_animation_markers`.

Example exported structure
--------------------------

```json
{
  "extensions": {
    "WEBGI_animation_markers": {
      "markers": [
        {
          "name": "cut_01",
          "frame": 42,
          "time": 1.4,
          "camera": 0,
          "marker_type": "scene"
        },
        {
          "name": "impact",
          "frame": 42,
          "time": 1.4,
          "marker_type": "pose",
          "animation": "fall"
        },
        {
          "name": "impact",
          "frame": 90,
          "time": 3.0,
          "marker_type": "pose",
          "animation": "fall"
        },
        {
          "name": "impact",
          "frame": 90,
          "time": 3.0,
          "marker_type": "pose",
          "animation": "idle"
        }
      ]
    }
  }
}
```

Notes:
- Scene timeline markers are exported with `marker_type: "scene"` and never include `animation`.
- Pose markers are exported with `marker_type: "pose"` and always include exactly one `animation`.
- If two pose markers are identical but belong to different animations, they are exported once per animation.
- `camera` is optional and is used only for scene markers.

Three.js Import
--------------

```typescript

class GLTFTimelineMarkersExtension implements GLTFLoaderPlugin {
    public name: string
    public parser: GLTFParser

    constructor(parser:GLTFParser) {
        this.parser = parser
        this.name = 'WEBGI_animation_markers'

    }
    async afterRoot(result: GLTF) {
        const markersData = this.parser.json.extensions?.[this.name]
        const sceneMarkers: any[] = []
        const poseMarkers: any[] = []

        for (const marker of markersData?.markers || []) {
            const markerType = marker.marker_type ?? 'scene'
            if (markerType === 'pose') {
                poseMarkers.push({
                    name: marker.name,
                    frame: marker.frame,
                    time: marker.time,
                    animation: marker.animation,
                    marker_type: 'pose',
                })
                continue
            }

            const camera = marker.camera !== undefined
                ? await this.parser.getDependency('camera', marker.camera)
                : undefined

            sceneMarkers.push({
                name: marker.name,
                frame: marker.frame,
                time: marker.time,
                camera,
                marker_type: 'scene',
            })
        }
        if (sceneMarkers.length < 1 && poseMarkers.length < 1) return

        const scene = result.scene ?? result.scenes[0]
        if (!scene) return
        scene.userData.sceneMarkers = sceneMarkers
        scene.userData.poseMarkers = poseMarkers

        if (sceneMarkers.length > 0) {
            const fps = 30
            const times = sceneMarkers.map(m => m.time ?? (m.frame / fps))
            let i = 0
            const values = sceneMarkers.map(() => i++)
            const duration = Math.max(...times) + 0.01

            let temp = -1
            const trackName = '.currentTimelineMarker'
            Object.defineProperty(scene, 'currentTimelineMarker', {
                get: ()=>temp,
                set: (v: any)=> scene.dispatchEvent({type: 'animationTimelineMarker', marker: sceneMarkers[temp = v]}),
            })
            const track = new NumberKeyframeTrack(trackName, times, values, InterpolateDiscrete)
            const anim = new AnimationClip('animationTimelineMarker', duration, [track])
            result.animations.push(anim)
        }
    }

}

gltfLoader.register((p)=>new GLTFTimelineMarkersExtension(p))
```