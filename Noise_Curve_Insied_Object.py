import maya.cmds as cmds
import maya.api.OpenMaya as om
import random
import math

# -------------------------------
# Functions
# -------------------------------
def get_random_farthest_points(mesh, min_distance=1.0):
    """
    Picks two random points on the mesh that are at least min_distance apart
    """
    verts = cmds.ls(f"{mesh}.vtx[*]", fl=True)
    max_attempts = 100
    for _ in range(max_attempts):
        start_v = random.choice(verts)
        end_v = random.choice(verts)
        pos_start = om.MVector(*cmds.pointPosition(start_v, w=True))
        pos_end = om.MVector(*cmds.pointPosition(end_v, w=True))
        if (pos_start - pos_end).length() >= min_distance:
            return pos_start, pos_end
    # fallback to farthest points
    start_v, end_v = get_farthest_points(mesh)
    return om.MVector(*cmds.pointPosition(start_v, w=True)), om.MVector(*cmds.pointPosition(end_v, w=True))

def get_farthest_points(mesh):
    verts = cmds.ls(f"{mesh}.vtx[*]", fl=True)
    max_dist = 0
    start_v = end_v = verts[0]
    for i in range(len(verts)):
        pos_i = om.MVector(*cmds.pointPosition(verts[i], w=True))
        for j in range(i+1, len(verts)):
            pos_j = om.MVector(*cmds.pointPosition(verts[j], w=True))
            dist = (pos_i - pos_j).length()
            if dist > max_dist:
                max_dist = dist
                start_v = verts[i]
                end_v = verts[j]
    return start_v, end_v

def apply_noise(t, noise_type, amplitude):
    """
    Apply selected noise type
    t : 0~1 along the curve
    amplitude : scale of noise
    """
    if noise_type == "Sin":
        return amplitude * math.sin(t * math.pi * 2 * random.uniform(1, 3))
    elif noise_type == "Fractal":
        value = 0
        for i in range(1, 4):
            value += (amplitude / i) * math.sin(t * math.pi * 2 * i + random.uniform(0, math.pi))
        return value
    elif noise_type == "Billow":
        value = 0
        for i in range(1, 3):
            value += (amplitude / i) * abs(math.sin(t * math.pi * 2 * i + random.uniform(0, math.pi)))
        return value
    else:
        return random.uniform(-amplitude, amplitude)

def create_noisy_curve(mesh, points_count=10, noise_amplitude=1.0, min_dist=1.0, noise_type="Sin"):
    start_pos, end_pos = get_random_farthest_points(mesh, min_distance=min_dist)
    curve_points = []
    for i in range(points_count):
        t = i / float(points_count-1)
        # first and last points stay exactly on the surface
        if i == 0:
            point = start_pos
        elif i == points_count - 1:
            point = end_pos
        else:
            point = start_pos + (end_pos - start_pos) * t
            # noise applied only to interior points
            nx = apply_noise(t, noise_type, noise_amplitude)
            ny = apply_noise(t, noise_type, noise_amplitude)
            nz = apply_noise(t, noise_type, noise_amplitude)
            point += om.MVector(nx, ny, nz)

        curve_points.append([point.x, point.y, point.z])

    return cmds.curve(p=curve_points, d=3)

# -------------------------------
# UI
# -------------------------------
def build_ui():
    win_name = "MultiNoisyCurveUI"
    if cmds.window(win_name, exists=True):
        cmds.deleteUI(win_name)

    cmds.window(win_name, title="Multi Noisy Curve Generator", widthHeight=(350, 300))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

    cmds.text(label="Select Mesh Object:")
    obj_field = cmds.textFieldButtonGrp('objField', buttonLabel='Load Selection', text="")
    def load_selection(*args):
        sel = cmds.ls(sl=True)
        if sel:
            cmds.textFieldButtonGrp(obj_field, edit=True, text=sel[0])
    cmds.textFieldButtonGrp(obj_field, edit=True, bc=load_selection)

    cmds.intSliderGrp('pointsSlider', label='Points per Curve', field=True, min=3, max=50, value=10)
    cmds.floatSliderGrp('noiseSlider', label='Noise Amplitude', field=True, min=0.0, max=5.0, value=1.0)
    cmds.floatSliderGrp('minDistSlider', label='Min Start/End Distance', field=True, min=0.1, max=10.0, value=1.0)
    cmds.intSliderGrp('numCurvesSlider', label='Number of Curves', field=True, min=1, max=20, value=3)

    cmds.optionMenuGrp('noiseTypeMenu', label='Noise Type')
    for ntype in ["Sin", "Fractal", "Billow", "Random"]:
        cmds.menuItem(label=ntype)

    def create_curves_btn(*args):
        mesh = cmds.textFieldButtonGrp(obj_field, q=True, text=True)
        points_count = cmds.intSliderGrp('pointsSlider', q=True, value=True)
        noise_amp = cmds.floatSliderGrp('noiseSlider', q=True, value=True)
        min_dist = cmds.floatSliderGrp('minDistSlider', q=True, value=True)
        num_curves = cmds.intSliderGrp('numCurvesSlider', q=True, value=True)
        noise_type = cmds.optionMenuGrp('noiseTypeMenu', q=True, value=True)

        if not cmds.objExists(mesh):
            cmds.warning("Mesh object not valid!")
            return

        for _ in range(num_curves):
            create_noisy_curve(mesh, points_count, noise_amp, min_dist, noise_type)

    cmds.button(label="Create Random Noisy Curves", command=create_curves_btn)
    cmds.showWindow(win_name)

# -------------------------------
# Run UI
# -------------------------------
build_ui()
