"""CATBRAIN placeholder concept art (original, low-poly, Blender 5.2 LTS).

Headless: /Applications/Blender.app/Contents/MacOS/Blender --background
  --factory-startup --python web/assets_src/render_cat_concept.py

Builds an original low-poly cat head (sphere + cones + emissive eyes) on a
dark lab backdrop. Deliberately placeholder-grade; UI copy labels it as such.
Saves web/assets/cat-concept.png and web/assets_src/cat-concept.blend.
"""

import math
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.dirname(HERE)
ASSETS_DIR = os.path.join(WEB_DIR, "assets")
PNG_OUT = os.path.join(ASSETS_DIR, "cat-concept.png")
BLEND_OUT = os.path.join(HERE, "cat-concept.blend")


def log(msg):
    print("[cat-concept] %s" % msg, flush=True)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights):
        for item in list(coll):
            coll.remove(item)


def matte(name, color, roughness=0.85):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def emissive(name, color, strength=3.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = strength
    mat.node_tree.links.new(emit.outputs[0], out.inputs[0])
    return mat


def shade_flat(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = False


def build_cat():
    fur = matte("Fur", (0.23, 0.22, 0.28, 1.0))
    glow = emissive("EyeGlow", (1.0, 0.62, 0.22, 1.0), strength=4.0)

    # Head: coarse UV sphere, slightly squashed.
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=12, ring_count=7, radius=1.0, location=(0, 0, 0.35)
    )
    head = bpy.context.active_object
    head.name = "CatHead"
    head.scale = (1.0, 0.88, 0.95)
    head.data.materials.append(fur)
    shade_flat(head)

    # Muzzle wedge: small flattened cube, same fur.
    bpy.ops.mesh.primitive_cube_add(size=0.62, location=(0, -0.72, 0.08))
    muzzle = bpy.context.active_object
    muzzle.name = "Muzzle"
    muzzle.scale = (1.0, 0.55, 0.62)
    muzzle.data.materials.append(fur)
    shade_flat(muzzle)

    # Ears: 4-sided cones, rotated to face forward.
    for side in (-1.0, 1.0):
        bpy.ops.mesh.primitive_cone_add(
            vertices=4, radius1=0.34, radius2=0.0, depth=0.72,
            location=(side * 0.58, 0.05, 1.28),
        )
        ear = bpy.context.active_object
        ear.name = "Ear_%s" % ("L" if side < 0 else "R")
        ear.rotation_euler = (0, side * -0.18, math.pi / 4)
        ear.data.materials.append(fur)
        shade_flat(ear)

    # Eyes: small emissive spheres.
    for side in (-1.0, 1.0):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=10, ring_count=6, radius=0.10,
            location=(side * 0.35, -0.78, 0.52),
        )
        eye = bpy.context.active_object
        eye.name = "Eye_%s" % ("L" if side < 0 else "R")
        eye.data.materials.append(glow)

    # Floor + backdrop: near-black lab void.
    void = matte("Void", (0.030, 0.030, 0.038, 1.0), roughness=1.0)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -0.85))
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.data.materials.append(void)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 6, 4))
    back = bpy.context.active_object
    back.name = "Backdrop"
    back.rotation_euler = (math.pi / 2, 0, 0)
    back.data.materials.append(void)


def build_lights():
    def area(name, energy, size, color, location):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = location
        return obj

    bpy.ops.object.empty_add(location=(0, 0, 0.35))
    aim = bpy.context.active_object
    aim.name = "LampTarget"
    key = area("Key", 220, 3.5, (1.0, 0.93, 0.82), (3.2, -3.2, 4.0))
    rim = area("Rim", 380, 2.5, (0.55, 0.75, 1.0), (-2.5, 4.5, 3.0))
    fill = area("Fill", 90, 4.0, (1.0, 1.0, 1.0), (0.0, -4.0, 1.2))
    for lamp in (key, rim, fill):
        track = lamp.constraints.new("TRACK_TO")
        track.target = aim
        track.track_axis = "TRACK_NEGATIVE_Z"
        track.up_axis = "UP_Y"


def build_camera():
    data = bpy.data.cameras.new("Camera")
    data.lens = 55
    cam = bpy.data.objects.new("Camera", data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0, -5.8, 1.1)
    bpy.ops.object.empty_add(location=(0, 0, 0.35))
    target = bpy.context.active_object
    target.name = "CamTarget"
    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    bpy.context.scene.camera = cam


def configure_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.cycles.device = "CPU"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 600
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = PNG_OUT
    world = bpy.context.scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.008, 0.008, 0.012, 1.0)
    bg.inputs["Strength"].default_value = 1.0


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    log("clearing scene")
    clear_scene()
    log("building cat")
    build_cat()
    log("building lights")
    build_lights()
    log("building camera")
    build_camera()
    log("configuring render")
    configure_render()
    log("rendering to %s" % PNG_OUT)
    bpy.ops.render.render(write_still=True)
    log("saving %s" % BLEND_OUT)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    if not os.path.exists(PNG_OUT):
        raise SystemExit("render produced no PNG")
    size = os.path.getsize(PNG_OUT)
    log("done: %s (%d bytes)" % (PNG_OUT, size))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - headless must report, not hang
        print("[cat-concept] FAILED: %r" % exc, flush=True)
        raise
