"""CATBRAIN concept art v0.4 — specimen-style hero CANDIDATE (do not ship).

Headless: /Applications/Blender.app/Contents/MacOS/Blender --background \
    --python web/assets_src/render_cat_v04.py -- .agents/audit/previews/v04-N.png
v0.4 goals vs v0.3: true 3/4 camera with negative space (v0.3 read frontal
and filled the frame), stronger chiaroscuro (dim key, dominant cool rim),
cooler slate body to sit on the site's near-black. Original placeholder art,
not a reconstruction. Manager approves before any swap of the live asset.
v04-6 = final manager cycle: grounded contact shadow (no float, no crop),
raised top-right-back rim (1-2px edge on ear/temple/cheek), eyes centered/
smaller/sunk into sockets.
"""
import math
import os
import sys

import bpy  # noqa: E402  # pylint: disable=import-error


def mat_principled(name, base_color, roughness=0.8, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def mat_emission(name, color, strength=3.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*color, 1.0)
    emit.inputs["Strength"].default_value = strength
    mat.node_tree.links.new(emit.outputs[0], out.inputs[0])
    return mat


def flat_shade(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = False


def place(obj, loc, rot=(0, 0, 0), scale=(1, 1, 1)):
    obj.location = loc
    obj.rotation_euler = rot
    obj.scale = scale


# --- clean slate -------------------------------------------------------
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
             bpy.data.cameras):
    for x in list(coll):
        coll.remove(x)

GRAY = mat_principled("CAT_Gray", (0.36, 0.40, 0.50))
LIGHT = mat_principled("CAT_Light", (0.58, 0.61, 0.68))
DARK = mat_principled("CAT_Dark", (0.06, 0.06, 0.08))
EYE = mat_emission("CAT_Eye", (1.0, 0.60, 0.14), 4.2)
NOSE = mat_principled("CAT_Nose", (0.16, 0.10, 0.12), roughness=0.5)

# --- head: wide-cheeked ico sphere --------------------------------------
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0)
head = bpy.context.active_object
head.name = "Head"
place(head, (0, 0, 0.95), scale=(1.02, 0.92, 0.86))
# Taper the cranium: narrow the top, keep the cheeks wide (sleeker v0.3).
mesh = head.data
for v in mesh.vertices:
    t = max(0.0, (v.co.z - 0.1)) * 0.28
    v.co.x *= (1.0 - t)
    v.co.y *= (1.0 - t * 0.6)
mesh.update()
head.data.materials.append(GRAY)
flat_shade(head)

# --- cheek pads: squashed spheres, overlapped INTO the head ------------------
for side in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=9, ring_count=5,
                                         radius=0.38)
    cheek = bpy.context.active_object
    cheek.name = "Cheek.%s" % ("L" if side < 0 else "R")
    place(cheek, (side * 0.66, 0.05, 0.42), scale=(1.0, 0.9, 0.95))
    cheek.data.materials.append(LIGHT)
    flat_shade(cheek)

# --- snout bump: muzzle grows OUT of the face ----------------------------------
bpy.ops.mesh.primitive_uv_sphere_add(segments=9, ring_count=5, radius=0.5)
snout = bpy.context.active_object
snout.name = "Snout"
place(snout, (0, 0.55, 0.55), scale=(1.0, 0.8, 0.85))
snout.data.materials.append(LIGHT)
flat_shade(snout)

# --- tapered muzzle: cube narrowed toward the top -------------------------
bpy.ops.mesh.primitive_cube_add(size=1.0)
muzzle = bpy.context.active_object
muzzle.name = "Muzzle"
place(muzzle, (0, 0.80, 0.58), scale=(0.44, 0.30, 0.28))
mesh = muzzle.data
for v in mesh.vertices:
    if v.co.z > 0.0:  # taper the top inward
        v.co.x *= 0.62
        v.co.y *= 0.80
mesh.update()
muzzle.data.materials.append(LIGHT)
flat_shade(muzzle)

# --- nose: explicit triangle mesh, apex DOWN (no rotation ambiguity) --------------
nose_mesh = bpy.data.meshes.new("NoseMesh")
nose_mesh.from_pydata(
    [(-0.10, 0.0, 0.06), (0.10, 0.0, 0.06), (0.0, 0.0, -0.10)],
    [], [(0, 1, 2)])
nose_mesh.update()
nose = bpy.data.objects.new("Nose", nose_mesh)
bpy.context.collection.objects.link(nose)
place(nose, (0, 1.00, 0.68))
nose.data.materials.append(NOSE)
flat_shade(nose)

# --- mouth: ONE ribbon mesh tracing the :3 (no rotation ambiguity) --------------
mouth_pts = [(-0.15, 0.44), (-0.06, 0.50), (0.0, 0.55),
             (0.06, 0.50), (0.15, 0.44), (0.0, 0.55), (0.0, 0.64)]
mouth_segs = [(0, 1), (1, 2), (2, 3), (3, 4), (2, 5), (5, 6)]
mouth_verts = []
mouth_faces = []
W2 = 0.016
for (a, b) in mouth_segs:
    (x1, z1), (x2, z2) = mouth_pts[a], mouth_pts[b]
    dx, dz = x2 - x1, z2 - z1
    ln = math.hypot(dx, dz) or 1.0
    nx, nz = -dz / ln * W2, dx / ln * W2
    i = len(mouth_verts)
    mouth_verts += [(x1 - nx, 0.0, z1 - nz), (x1 + nx, 0.0, z1 + nz),
                    (x2 + nx, 0.0, z2 + nz), (x2 - nx, 0.0, z2 - nz)]
    mouth_faces.append((i, i + 1, i + 2, i + 3))
mouth_mesh = bpy.data.meshes.new("MouthMesh")
mouth_mesh.from_pydata(mouth_verts, [], mouth_faces)
mouth_mesh.update()
mouth = bpy.data.objects.new("Mouth", mouth_mesh)
bpy.context.collection.objects.link(mouth)
place(mouth, (0, 0.985, 0.0))
mouth.data.materials.append(DARK)

# --- almond eyes + flush slit pupils ----------------------------------------
# v04-6 (manager final fix 3): pulled further toward facial center
# (|x| 0.30 -> 0.26), shrunk ~10% (r 0.20 -> 0.18), and sunk DEEPER into the
# head shell (y 0.80 -> 0.85; shell surface at this x/z is y~0.88, so only a
# ~0.06 almond cap is proud of the mesh — no float, no pasted look). Mesh is
# mirrored exactly; the 3/4 perspective supplies the natural asymmetry.
for side in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6,
                                         radius=0.18)
    eye = bpy.context.active_object
    eye.name = "Eye.%s" % ("L" if side < 0 else "R")
    place(eye, (side * 0.26, 0.85, 1.10),
          rot=(0, 0, side * math.radians(-14)),
          scale=(1.5, 0.50, 0.85))
    eye.data.materials.append(EYE)
    flat_shade(eye)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    pupil = bpy.context.active_object
    pupil.name = "Pupil.%s" % ("L" if side < 0 else "R")
    place(pupil, (side * 0.26, 0.945, 1.115),
          rot=(0, 0, side * math.radians(-14)),
          scale=(0.020, 0.03, 0.15))
    pupil.data.materials.append(DARK)
    flat_shade(pupil)
    # Catchlight: tiny emissive dot, upper-outer corner of each eye.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=3,
                                         radius=0.033)
    glint = bpy.context.active_object
    glint.name = "Glint.%s" % ("L" if side < 0 else "R")
    place(glint, (side * 0.205, 0.955, 1.170))
    glint.data.materials.append(
        mat_emission("CAT_Glint", (1.0, 1.0, 1.0), 5.0))
    flat_shade(glint)

# (v0.3b: brow slabs removed — they read angry and floated off the surface.)

# --- ears: thick 5-sided cones, angled forward/outward + inner ear ----------
for side in (-1, 1):
    bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=0.34, depth=0.78)
    ear = bpy.context.active_object
    ear.name = "Ear.%s" % ("L" if side < 0 else "R")
    place(ear, (side * 0.58, 0.15, 1.72),
          rot=(math.radians(-20), 0, side * math.radians(-18)))
    ear.data.materials.append(GRAY)
    flat_shade(ear)
    bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=0.17, depth=0.45)
    inner = bpy.context.active_object
    inner.name = "InnerEar.%s" % ("L" if side < 0 else "R")
    place(inner, (side * 0.55, 0.28, 1.66),
          rot=(math.radians(-20), 0, side * math.radians(-18)))
    inner.data.materials.append(DARK)
    flat_shade(inner)

# --- grounding (v04-6, manager final fix 1): floor RAISED to kiss the lowest
# geometry (cheek shells bottom out at z=0.059; plane at 0.060 -> true
# contact, zero gap, no float) + a TIGHT soft spot directly overhead so the
# contact-shadow pool sits immediately under the bust and stays fully inside
# the frame (v04-5's pool was offset, detached, and cropped at frame bottom).
# Kept near-black: specimen-in-a-void, no horizon band (v04-1's mistake).
bpy.ops.mesh.primitive_plane_add(size=200)  # edge far outside frame: no band
floor = bpy.context.active_object
floor.name = "Floor"
place(floor, (0, 0, 0.060))
floor.data.materials.append(
    mat_principled("CAT_Floor", (0.006, 0.008, 0.012), roughness=0.34))

# --- lights: dim warm key, dominant cool rim, faint fill/kick -------------------
# NOTE: face looks toward +Y, so the key/fill sit at +Y, rim behind at -Y.
# v04-5 (manager fix 2): key dimmed 380 -> 190 so the emissive eyes carry the
# face; rim pushed higher/farther frame-top-right and more than doubled.
bpy.ops.object.light_add(type="AREA", location=(4.5, 3.5, 5.2))
key = bpy.context.active_object
key.name = "Key"
key.data.energy = 190
key.data.size = 3.5
key.data.color = (1.0, 0.90, 0.78)

bpy.ops.object.light_add(type="SPOT", location=(-5.2, -0.8, 6.8))
rim = bpy.context.active_object
rim.name = "Rim"
rim.data.energy = 14000
rim.data.color = (0.55, 0.72, 1.0)
rim.data.spot_size = math.radians(38)
bpy.ops.object.empty_add(location=(-0.7, 0, 0.95))
focus = bpy.context.active_object
focus.name = "Focus"
# v04-6 (manager final fix 2): rim raised + swung top-right-BACK (in frame
# space) and re-aimed at the ear/temple line via its own target, so it carves
# a 1-2px cool edge on the right ear + temple + cheek silhouette that no
# longer melts into the void.
bpy.ops.object.empty_add(location=(-0.55, 0.1, 1.35))
rimfocus = bpy.context.active_object
rimfocus.name = "RimFocus"
track = rim.constraints.new("TRACK_TO")
track.target = rimfocus
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"

bpy.ops.object.light_add(type="POINT", location=(-2.4, 3.0, 1.2))
fill = bpy.context.active_object
fill.name = "Fill"
fill.data.energy = 80
fill.data.color = (0.70, 0.78, 1.0)

# Faint cool under-kick: separates the chin/jaw silhouette from the void.
# (v04-6: lifted above the raised floor — it was occluded at z=-1.2.)
bpy.ops.object.light_add(type="POINT", location=(1.4, 2.8, 0.6))
kick = bpy.context.active_object
kick.name = "Kick"
kick.data.energy = 50
kick.data.color = (0.35, 0.48, 0.72)

# Soft overhead spot: its job is the pool/shadow on the floor, not the head.
# v04-6: centered straight over the bust (shadow lands directly beneath, no
# detachment), tightened (36deg) so the whole pool + soft shadow stay inside
# the frame (no cropping), shadow_soft_size up for a soft contact edge.
bpy.ops.object.light_add(type="SPOT", location=(0.0, 0.2, 6.8))
down = bpy.context.active_object
down.name = "DownPool"
down.data.energy = 160
down.data.color = (0.80, 0.87, 1.0)
down.data.spot_size = math.radians(36)
try:
    down.data.shadow_soft_size = 0.6
except AttributeError:
    pass

# --- camera: true 3/4, specimen floating in a void ------------------------------
# Head sits right-of-center (focus nudged -x), ~35 deg off-axis, ear tips and
# chin both comfortably inside frame, generous negative space above/left.
bpy.ops.object.camera_add(location=(6.2, 7.6, 2.8))
cam = bpy.context.active_object
cam.name = "Camera"
ctrack = cam.constraints.new("TRACK_TO")
ctrack.target = focus
ctrack.track_axis = "TRACK_NEGATIVE_Z"
ctrack.up_axis = "UP_Y"
bpy.context.scene.camera = cam
cam.data.lens = 70

# --- world + render settings ---------------------------------------------------
world = bpy.context.scene.world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (
    0.014, 0.017, 0.024, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
try:
    scene.eevee.taa_render_samples = 64
except AttributeError:
    pass
try:  # Eevee Next raytracing: enables the faint floor reflection (optional).
    scene.eevee.use_raytracing = True
except AttributeError:
    pass

# --- output --------------------------------------------------------------------
argv = [a for a in sys.argv if a.endswith(".png")]
out = (argv[-1] if argv else
       "/Users/mtg/Desktop/CATBRAIN/.agents/audit/previews/v04-1.png")
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("CATBRAIN v0.4 render written to %s" % scene.render.filepath)
blend_out = os.path.splitext(out)[0] + ".blend"
try:
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
    print("CATBRAIN scene saved to %s" % blend_out)
except Exception as ex:  # noqa: BLE001
    print("CATBRAIN blend save skipped: {!r}".format(ex))
