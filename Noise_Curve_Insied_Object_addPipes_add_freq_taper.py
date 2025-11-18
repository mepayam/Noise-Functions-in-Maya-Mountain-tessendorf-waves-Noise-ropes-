import maya.cmds as cmds
import maya.api.OpenMaya as om
import random
import math

# -------------------------------
# Noise Functions
# -------------------------------
def apply_noise(t, noise_type, amplitude, frequency=1.0, taper=True, offset=0.0):
    """
    Apply selected noise type along the curve
    """
    t_adj = t * frequency + offset
    taper_factor = math.sin(t * math.pi) if taper else 1.0

    if noise_type == "Sin":
        return amplitude * taper_factor * math.sin(t_adj * math.pi * 2 * random.uniform(1, 3))
    elif noise_type == "Fractal":
        value = 0
        for i in range(1, 4):
            value += (amplitude / i) * taper_factor * math.sin(t_adj * math.pi * 2 * i + random.uniform(0, math.pi))
        return value
    elif noise_type == "Billow":
        value = 0
        for i in range(1, 3):
            value += (amplitude / i) * taper_factor * abs(math.sin(t_adj * math.pi * 2 * i + random.uniform(0, math.pi)))
        return value
    elif noise_type == "Wave":
        return amplitude * taper_factor * math.sin(t_adj * math.pi * 4 + random.uniform(0, math.pi))
    elif noise_type == "Wispy":
        return amplitude * taper_factor * 0.3 * math.sin(t_adj * math.pi * 10 + random.uniform(0, math.pi)) + random.uniform(-amplitude*0.1, amplitude*0.1)
    elif noise_type == "Spacetime":
        value = 0
        for i in range(1, 5):
            value += (amplitude / i) * taper_factor * math.sin(t_adj * math.pi * 2 * i + random.uniform(0, math.pi))
        value += random.uniform(-amplitude*0.3, amplitude*0.3)
        return value
    else:  # Random
        return random.uniform(-amplitude, amplitude)

# -------------------------------
# Curve / Pipe Functions
# -------------------------------
def get_random_farthest_points(mesh, min_distance=1.0):
    verts = cmds.ls(f"{mesh}.vtx[*]", fl=True)
    max_attempts = 100
    for _ in range(max_attempts):
        start_v = random.choice(verts)
        end_v = random.choice(verts)
        pos_start = om.MVector(*cmds.pointPosition(start_v, w=True))
        pos_end = om.MVector(*cmds.pointPosition(end_v, w=True))
        if (pos_start - pos_end).length() >= min_distance:
            return pos_start, pos_end
    return om.MVector(*cmds.pointPosition(verts[0], w=True)), om.MVector(*cmds.pointPosition(verts[-1], w=True))

def create_noisy_curve(mesh, points_count=10, noise_amplitude=1.0, min_dist=1.0,
                       noise_type="Sin", frequency=1.0, offset=0.0):
    start_pos, end_pos = get_random_farthest_points(mesh, min_distance=min_dist)
    curve_points = []
    for i in range(points_count):
        t = i / float(points_count-1)
        if i == 0:
            point = start_pos
        elif i == points_count - 1:
            point = end_pos
        else:
            point = start_pos + (end_pos - start_pos) * t
            nx = apply_noise(t, noise_type, noise_amplitude, frequency, taper=True, offset=offset)
            ny = apply_noise(t, noise_type, noise_amplitude, frequency, taper=True, offset=offset)
            nz = apply_noise(t, noise_type, noise_amplitude, frequency, taper=True, offset=offset)
            point += om.MVector(nx, ny, nz)
        curve_points.append([point.x, point.y, point.z])
    curve = cmds.curve(p=curve_points, d=3)
    return curve

def curve_to_pipe(curve, radius=0.1, sections=8):
    circle = cmds.circle(normal=[0,1,0], radius=radius, sections=sections)[0]
    pipe = cmds.extrude(circle, curve, constructionHistory=True, polygon=1,
                         scale=1, fixedPath=True, useComponentPivot=True)[0]
    cmds.delete(pipe, ch=True)
    if cmds.objExists(circle):
        cmds.delete(circle)
    return pipe

# -------------------------------
# UI
# -------------------------------
def build_ui():
    win_name = "AdvancedNoisyCurveUI"
    if cmds.window(win_name, exists=True):
        cmds.deleteUI(win_name)

    cmds.window(win_name, title="Advanced Noisy Curve Generator", widthHeight=(400, 380))
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
    cmds.floatSliderGrp('freqSlider', label='Noise Frequency / Scale', field=True, min=1.0, max=10.0, value=1.0)
    cmds.floatSliderGrp('minDistSlider', label='Min Start/End Distance', field=True, min=0.1, max=10.0, value=1.0)
    cmds.intSliderGrp('numCurvesSlider', label='Number of Curves', field=True, min=1, max=20, value=3)
    cmds.floatSliderGrp('pipeRadiusSlider', label='Pipe Radius', field=True, min=0.01, max=2.0, value=0.1)

    cmds.optionMenuGrp('noiseTypeMenu', label='Noise Type')
    for ntype in ["Sin", "Fractal", "Billow", "Wave", "Wispy", "Spacetime", "Random"]:
        cmds.menuItem(label=ntype)

    def create_curves_btn(*args):
        mesh = cmds.textFieldButtonGrp(obj_field, q=True, text=True)
        points_count = cmds.intSliderGrp('pointsSlider', q=True, value=True)
        noise_amp = cmds.floatSliderGrp('noiseSlider', q=True, value=True)
        freq = cmds.floatSliderGrp('freqSlider', q=True, value=True)
        min_dist = cmds.floatSliderGrp('minDistSlider', q=True, value=True)
        num_curves = cmds.intSliderGrp('numCurvesSlider', q=True, value=True)
        pipe_radius = cmds.floatSliderGrp('pipeRadiusSlider', q=True, value=True)
        noise_type = cmds.optionMenuGrp('noiseTypeMenu', q=True, value=True)

        if not cmds.objExists(mesh):
            cmds.warning("Mesh object not valid!")
            return

        curve_group = cmds.group(empty=True, name="Curves_Group")
        pipe_group = cmds.group(empty=True, name="Pipes_Group")

        for _ in range(num_curves):
            curve = create_noisy_curve(mesh, points_count, noise_amp, min_dist, noise_type,
                                       frequency=freq, offset=0.0)
            cmds.parent(curve, curve_group)
            pipe = curve_to_pipe(curve, radius=pipe_radius)
            cmds.parent(pipe, pipe_group)

    cmds.button(label="Create Advanced Curves + Pipes", command=create_curves_btn)
    cmds.showWindow(win_name)

# -------------------------------
# Run UI
# -------------------------------
build_ui()
