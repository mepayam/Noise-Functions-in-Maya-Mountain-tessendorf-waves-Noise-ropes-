import maya.cmds as cmds
import maya.api.OpenMaya as om
import math
from itertools import combinations
import random

# Attempt to import Perlin noise library
try:
    from noise import pnoise1
except ImportError:
    cmds.warning("Python 'noise' library not installed. Using random noise instead.")
    def pnoise1(x):
        return random.uniform(-1,1)

# -------------------------
# Mesh center extraction
# -------------------------
def get_mesh_centers(obj):
    sel = om.MSelectionList()
    sel.add(obj)
    dag = sel.getDagPath(0)
    dag.extendToShape()
    fnMesh = om.MFnMesh(dag)

    all_faces = set(range(fnMesh.numPolygons))
    vert_to_face = {}
    for f in range(fnMesh.numPolygons):
        for v in fnMesh.getPolygonVertices(f):
            vert_to_face.setdefault(v,set()).add(f)

    components = []
    while all_faces:
        start = all_faces.pop()
        stack = [start]
        comp_faces = set([start])
        while stack:
            f = stack.pop()
            verts = fnMesh.getPolygonVertices(f)
            neighbors = set()
            for v in verts:
                neighbors.update(vert_to_face[v])
            neighbors -= comp_faces
            stack.extend(neighbors)
            comp_faces.update(neighbors)
        components.append(list(comp_faces))
        all_faces -= comp_faces

    centers = []
    for comp in components:
        vert_ids = set()
        for f in comp:
            vert_ids.update(fnMesh.getPolygonVertices(f))
        verts = [om.MVector(fnMesh.getPoint(v)) for v in vert_ids]
        center = sum(verts, om.MVector(0,0,0))/len(verts)
        centers.append(center)

    centers = sorted(centers, key=lambda v: v.x)
    return centers

# -------------------------
# Arc curve creation with 3D noise
# -------------------------
def create_arc_curve_between_points(p0, p1, num_cvs=7, sag_amount=-2.0, noise_amp=0.0, noise_freq=1.0):
    points = []
    for i in range(num_cvs):
        t = i / (num_cvs-1)
        pos = p0*(1-t) + p1*t
        points.append((pos.x,pos.y,pos.z))

    curve = cmds.curve(p=points, d=1)

    # Apply arc sag in Y + 3D noise
    for i in range(num_cvs):
        t = i / (num_cvs-1)
        arc_y = math.sin(math.pi * t) * sag_amount
        # 3D Perlin noise
        noise_x = pnoise1(t * noise_freq + 100) * noise_amp
        noise_y = pnoise1(t * noise_freq + 200) * noise_amp
        noise_z = pnoise1(t * noise_freq + 300) * noise_amp
        cmds.move(noise_x, arc_y + noise_y, noise_z, curve + f".cv[{i}]", r=True)

    return curve

# -------------------------
# Rope creation
# -------------------------
def create_rope(obj, num_cvs=7, sag_amount=-2.0, full_mesh=False, noise_amp=0.0, noise_freq=1.0, curve_to_curve=False):
    centers = get_mesh_centers(obj)
    if not centers or len(centers) < 2:
        cmds.warning("Not enough spheres found to create curves.")
        return []

    all_curves = []

    # --- Step 1: curves connecting spheres ---
    if full_mesh:
        sphere_pairs = list(combinations(centers, 2))
    else:
        sphere_pairs = [(centers[i], centers[i+1]) for i in range(len(centers)-1)]

    sphere_curves = []
    for p0, p1 in sphere_pairs:
        crv = create_arc_curve_between_points(p0, p1, num_cvs, sag_amount, noise_amp, noise_freq)
        sphere_curves.append(crv)
    all_curves.extend(sphere_curves)

    # --- Step 2: optional curves connecting curve centers ---
    if curve_to_curve and sphere_curves:
        curve_centers = []
        for crv in sphere_curves:
            cvs = cmds.ls(crv + ".cv[:]", fl=True)
            mid_idx = len(cvs)//2
            pos = cmds.pointPosition(cvs[mid_idx], w=True)
            curve_centers.append(om.MVector(*pos))

        for p0, p1 in combinations(curve_centers, 2):
            crv = create_arc_curve_between_points(p0, p1, num_cvs, sag_amount, noise_amp, noise_freq)
            all_curves.append(crv)

    # --- Step 3: Group all created curves ---
    if all_curves:
        if cmds.objExists("Rope_Curves_GRP"):
            cmds.delete("Rope_Curves_GRP")  # optional: remove previous group
        grp = cmds.group(all_curves, name="Rope_Curves_GRP")
        print(f"✔ Created {len(all_curves)} curves. Grouped under '{grp}'")
    else:
        print("⚠ No curves created.")

    return all_curves

# -------------------------
# UI
# -------------------------
def ropeUI():
    win = "ropeArcUI"
    if cmds.window(win, exists=True):
        cmds.deleteUI(win)

    cmds.window(win, title="Arc Rope Between Spheres", widthHeight=(400,360))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)

    cmds.text(label="Select your combined spheres mesh.", align="center")
    cmds.button(label="Load Selected Object", height=30, command=lambda *_: load_selected_object())
    cmds.textField("ropeObjField", placeholderText="No object loaded", editable=False)

    cmds.intSliderGrp("numCVs", label="CVs per Curve", field=True, min=3, max=50, value=7)
    cmds.floatSliderGrp("sagAmount", label="Sag Amount (Y)", field=True, min=-10, max=0, value=-2)

    cmds.optionMenu("modeOption", label="Connection Mode")
    cmds.menuItem(label="Linear (N-1 curves)")
    cmds.menuItem(label="Full Mesh (N*(N-1)/2 curves)")

    # Noise controls
    cmds.floatSliderGrp("noiseAmp", label="Noise Amplitude", field=True, min=0, max=5, value=0)
    cmds.floatSliderGrp("noiseFreq", label="Noise Frequency", field=True, min=0, max=10, value=1)

    # Checkbox for optional curve-to-curve connections
    cmds.checkBox("curveToCurveCB", label="Connect Curve Centers", value=False)

    cmds.button(label="Create Rope Curves", height=40, bgc=(0.3,0.6,0.3), command=lambda *_: run_rope())

    cmds.setParent("..")
    cmds.showWindow(win)

def load_selected_object():
    sel = cmds.ls(sl=True)
    if not sel:
        cmds.warning("Select the combined spheres mesh first.")
        return
    cmds.textField("ropeObjField", e=True, text=sel[0])

def run_rope():
    obj = cmds.textField("ropeObjField", q=True, text=True)
    if not obj:
        cmds.warning("No object loaded")
        return
    num_cvs = cmds.intSliderGrp("numCVs", q=True, value=True)
    sag_amount = cmds.floatSliderGrp("sagAmount", q=True, value=True)
    mode = cmds.optionMenu("modeOption", q=True, value=True)
    noise_amp = cmds.floatSliderGrp("noiseAmp", q=True, value=True)
    noise_freq = cmds.floatSliderGrp("noiseFreq", q=True, value=True)
    curve_to_curve = cmds.checkBox("curveToCurveCB", q=True, value=True)

    full_mesh = True if mode=="Full Mesh (N*(N-1)/2 curves)" else False
    create_rope(obj, num_cvs, sag_amount, full_mesh, noise_amp, noise_freq, curve_to_curve)

# -------------------------
# Start UI
# -------------------------
ropeUI()
