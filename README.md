[![Blender](misc/Blender_logo.png)](http://www.blender.org/) [![glTF](misc/glTF_logo.png)](https://www.khronos.org/gltf/) [![three.js](misc/threejs_logo.png)](https://threejs.org/)

GLTF Timeline Markers extension
======================================

Custom extension to support animation timeline markers with camera binding support in GLTF/GLB.

[Blender Addon](./__init__.py)
--------------
Put this folder in the python addons directory in blender.

For Mac its `/Applications/Blender.app/Contents/Resources/<version>/scripts/addons`
For Linux `/home/<username>/.config/blender/<version>/scripts/addons`

The markers are exported at the glTF document root inside `extensions.WEBGI_animation_markers`

Example exported structure
--------------------------

```json
{
  "extensions": {
    "WEBGI_animation_markers": {
      "markers": [
        {
          "name": "impact_1",
          "frame": 42,
          "time": 1.4,
          "camera": 0,
          "animation": "fall"
        },
        {
          "name": "impact_2",
          "frame": 90,
          "time": 3.0,
          "camera": 0,
          "animation": "fall"
        },
        {
          "name": "impact_2",
          "frame": 90,
          "time": 3.0,
          "camera": 0,
          "animation": "idle"
        }
      ]
    }
  }
}
```

Notes:
- Each marker entry carries exactly one `animation` value.
- If a marker falls into multiple animation ranges, the exporter emits one marker entry per matching animation.
- `camera` is optional and is resolved to the exported camera index when present.

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
        const markers: any[] = []

        for (const marker of markersData?.markers || []) {
            const camera = marker.camera !== undefined ? await this.parser.getDependency('camera', marker.camera) : undefined
            markers.push({
                name: marker.name,
                frame: marker.frame,
                time: marker.time,
                camera,
                animation: marker.animation,
            })
        }
        if (markers.length < 1) return

        const scene = result.scene ?? result.scenes[0]
        if (!scene) return
        scene.userData.markers = markers

        const fps = 30
        const times = markers.map(m=>m.frame / fps)
        let i = 0
        const values = markers.map(m=>i++)
        const duration = Math.max(...times) + 0.01

        let temp = -1
        const trackName = '.currentTimelineMarker'
        Object.defineProperty(scene, 'currentTimelineMarker', {
            get: ()=>temp,
            set: (v: any)=> scene.dispatchEvent({type: 'animationTimelineMarker', marker: markers[temp = v]}),
        })
        const track = new NumberKeyframeTrack(trackName, times, values, InterpolateDiscrete)
        const anim = new AnimationClip('animationTimelineMarker', duration, [track])
        result.animations.push(anim)
    }

}

gltfLoader.register((p)=>new GLTFTimelineMarkersExtension(p))
```