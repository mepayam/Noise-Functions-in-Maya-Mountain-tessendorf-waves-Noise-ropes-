import maya.cmds as cmds
import maya.api.OpenMaya as om
import math
import random

# ----------------------------
# Simplex Noise
# ----------------------------
class SimplexNoise:
    def __init__(self, seed=0):
        self.grad3 = [[1,1,0],[-1,1,0],[1,-1,0],[-1,-1,0],
                      [1,0,1],[-1,0,1],[1,0,-1],[-1,0,-1],
                      [0,1,1],[0,-1,1],[0,1,-1],[0,-1,-1]]
        self.p = [i for i in range(256)]
        random.Random(seed).shuffle(self.p)
        self.perm = self.p*2

    def dot(self, g, x, y, z):
        return g[0]*x + g[1]*y + g[2]*z

    def noise3d(self, xin, yin, zin):
        F3 = 1.0/3.0
        G3 = 1.0/6.0
        s = (xin+yin+zin)*F3
        i = math.floor(xin+s)
        j = math.floor(yin+s)
        k = math.floor(zin+s)
        t = (i+j+k)*G3
        X0 = i-t
        Y0 = j-t
        Z0 = k-t
        x0 = xin-X0
        y0 = yin-Y0
        z0 = zin-Z0
        if x0>=y0:
            if y0>=z0:
                i1,j1,k1 = 1,0,0
                i2,j2,k2 = 1,1,0
            elif x0>=z0:
                i1,j1,k1 = 1,0,0
                i2,j2,k2 = 1,0,1
            else:
                i1,j1,k1 = 0,0,1
                i2,j2,k2 = 1,0,1
        else:
            if y0<z0:
                i1,j1,k1 = 0,0,1
                i2,j2,k2 = 0,1,1
            elif x0<z0:
                i1,j1,k1 = 0,1,0
                i2,j2,k2 = 0,1,1
            else:
                i1,j1,k1 = 0,1,0
                i2,j2,k2 = 1,1,0
        x1 = x0 - i1 + G3
        y1 = y0 - j1 + G3
        z1 = z0 - k1 + G3
        x2 = x0 - i2 + 2.0*G3
        y2 = y0 - j2 + 2.0*G3
        z2 = z0 - k2 + 2.0*G3
        x3 = x0 -1.0 +3.0*G3
        y3 = y0 -1.0 +3.0*G3
        z3 = z0 -1.0 +3.0*G3
        ii = i & 255
        jj = j & 255
        kk = k & 255
        gi0 = self.perm[ii+self.perm[jj+self.perm[kk]]] % 12
        gi1 = self.perm[ii+i1+self.perm[jj+j1+self.perm[kk+k1]]] % 12
        gi2 = self.perm[ii+i2+self.perm[jj+j2+self.perm[kk+k2]]] % 12
        gi3 = self.perm[ii+1+self.perm[jj+1+self.perm[kk+1]]] % 12
        t0 = 0.6 - x0*x0 - y0*y0 - z0*z0
        n0 = (t0*t0*t0*t0*self.dot(self.grad3[gi0], x0, y0, z0)) if t0>0 else 0.0
        t1 = 0.6 - x1*x1 - y1*y1 - z1*z1
        n1 = (t1*t1*t*t*self.dot(self.grad3[gi1], x1, y1, z1)) if t1>0 else 0.0
        t2 = 0.6 - x2*x2 - y2*y2 - z2*z2
        n2 = (t2*t2*t2*t2*self.dot(self.grad3[gi2], x2, y2, z2)) if t2>0 else 0.0
        t3 = 0.6 - x3*x3 - y3*y3 - z3*z3
        n3 = (t3*t3*t3*t3*self.dot(self.grad3[gi3], x3, y3, z3)) if t3>0 else 0.0
        return 32.0*(n0+n1+n2+n3)

# ----------------------------
# Cellular Noise
# ----------------------------
def cellular_noise(p, cell_size=1.0, metric='manhattan', seed=0):
    xi = math.floor(p[0]/cell_size)
    yi = math.floor(p[1]/cell_size)
    zi = math.floor(p[2]/cell_size)
    min_dist = float('inf')
    random.seed(seed)
    for dx in range(-1,2):
        for dy in range(-1,2):
            for dz in range(-1,2):
                cx = xi+dx + random.random()
                cy = yi+dy + random.random()
                cz = zi+dz + random.random()
                if metric=='manhattan':
                    d = abs(p[0]-cx*cell_size)+abs(p[1]-cy*cell_size)+abs(p[2]-cz*cell_size)
                else:  # Chebyshev
                    d = max(abs(p[0]-cx*cell_size), abs(p[1]-cy*cell_size), abs(p[2]-cz*cell_size))
                if d < min_dist:
                    min_dist = d
    return min_dist

# ----------------------------
# Sparse Convolution Noise
# ----------------------------
def sparse_convolution_noise(p, cell_size=1.0, seed=0):
    xi = math.floor(p[0]/cell_size)
    yi = math.floor(p[1]/cell_size)
    zi = math.floor(p[2]/cell_size)
    value = 0
    random.seed(seed)
    for dx in range(-1,2):
        for dy in range(-1,2):
            for dz in range(-1,2):
                cx = xi+dx + random.random()
                cy = yi+dy + random.random()
                cz = zi+dz + random.random()
                dist = math.sqrt((p[0]-cx*cell_size)**2 + (p[1]-cy*cell_size)**2 + (p[2]-cz*cell_size)**2)
                value += math.exp(-dist*dist*4)
    return value / 27.0

# ----------------------------
# Cell Noise
# ----------------------------
def cell_noise(p, cell_size=1.0, seed=0):
    xi = math.floor(p[0]/cell_size)
    yi = math.floor(p[1]/cell_size)
    zi = math.floor(p[2]/cell_size)
    random.seed(xi*73856093 ^ yi*19349663 ^ zi*83492791 ^ seed)
    return random.random()

# ----------------------------
# Worley (Euclidean) Cellular F1
# ----------------------------
def worley_noise(p, cell_size=1.0, seed=0):
    xi = math.floor(p[0]/cell_size)
    yi = math.floor(p[1]/cell_size)
    zi = math.floor(p[2]/cell_size)
    min_dist = float('inf')
    random.seed(seed)
    for dx in range(-1,2):
        for dy in range(-1,2):
            for dz in range(-1,2):
                cx = xi + dx + random.random()
                cy = yi + dy + random.random()
                cz = zi + dz + random.random()
                d = math.sqrt((p[0]-cx*cell_size)**2 + (p[1]-cy*cell_size)**2 + (p[2]-cz*cell_size)**2)
                if d < min_dist:
                    min_dist = d
    return min_dist

# ----------------------------
# UI
# ----------------------------
def create_mountain_ui():
    if cmds.window("mountainWin", exists=True):
        cmds.deleteUI("mountainWin")
    cmds.window("mountainWin", title="Mountain Noise Deformer", widthHeight=(380, 360))
    cmds.columnLayout(adjustableColumn=True)
    cmds.text(label="Select a mesh to apply Mountain Noise")
    
    # Noise type
    cmds.optionMenu("noiseType", label="Noise Type")
    cmds.menuItem(label="Simplex")
    cmds.menuItem(label="Manhattan Cellular F1")
    cmds.menuItem(label="Chebyshev Cellular F1")
    cmds.menuItem(label="Sparse Convolution Noise")
    cmds.menuItem(label="Cell Noise")
    cmds.menuItem(label="Worley Cellular Noise F1")
    
    cmds.floatSliderGrp("amplitude", label="Amplitude", field=True, minValue=0.0, maxValue=10.0, value=1.0)
    cmds.floatSliderGrp("elementSize", label="Element Size", field=True, minValue=0.01, maxValue=100.0, value=1.0)
    cmds.floatSliderGrp("offset", label="Offset", field=True, minValue=0.0, maxValue=100.0, value=0.0)
    cmds.intSliderGrp("seed", label="Seed", field=True, minValue=0, maxValue=9999, value=0)
    
    cmds.optionMenu("rangeValue", label="Range Value")
    cmds.menuItem(label="Zero Center")
    cmds.menuItem(label="Positive")
    
    cmds.button(label="Apply Mountain", command=lambda x: apply_mountain())
    cmds.showWindow("mountainWin")

# ----------------------------
# Apply Mountain
# ----------------------------
def apply_mountain():
    selection = cmds.ls(sl=True, type="transform")
    if not selection:
        cmds.warning("Please select a mesh!")
        return
    mesh = selection[0]
    amplitude = cmds.floatSliderGrp("amplitude", query=True, value=True)
    element_size = cmds.floatSliderGrp("elementSize", query=True, value=True)
    offset = cmds.floatSliderGrp("offset", query=True, value=True)
    seed = cmds.intSliderGrp("seed", query=True, value=True)
    noise_type = cmds.optionMenu("noiseType", query=True, value=True)
    range_value = cmds.optionMenu("rangeValue", query=True, value=True)
    
    simplex = SimplexNoise(seed)
    
    selList = om.MSelectionList()
    selList.add(mesh)
    dagPath = selList.getDagPath(0)
    mfnMesh = om.MFnMesh(dagPath)
    
    verts = mfnMesh.getPoints(om.MSpace.kWorld)
    normals = mfnMesh.getVertexNormals(True, om.MSpace.kWorld)
    newVerts = om.MPointArray()
    
    for v, n in zip(verts, normals):
        p = ((v.x+offset)/element_size, (v.y+offset)/element_size, (v.z+offset)/element_size)
        
        if noise_type == "Simplex":
            n_value = simplex.noise3d(*p)
        elif noise_type == "Manhattan Cellular F1":
            n_value = cellular_noise(p, element_size, metric='manhattan', seed=seed)
        elif noise_type == "Chebyshev Cellular F1":
            n_value = cellular_noise(p, element_size, metric='chebyshev', seed=seed)
        elif noise_type == "Sparse Convolution Noise":
            n_value = sparse_convolution_noise(p, element_size, seed=seed)
        elif noise_type == "Cell Noise":
            n_value = cell_noise(p, element_size, seed=seed)
        elif noise_type == "Worley Cellular Noise F1":
            n_value = worley_noise(p, element_size, seed=seed)
        
        # Apply Range Value
        if range_value == "Zero Center":
            if "Cellular" in noise_type or "Sparse" in noise_type or "Cell" in noise_type or "Worley" in noise_type:
                n_value = n_value - 0.5
        elif range_value == "Positive":
            if "Simplex" in noise_type:
                n_value = (n_value + 1.0)/2.0
        
        newVerts.append(om.MPoint(v.x + n_value * amplitude * n.x,
                                  v.y + n_value * amplitude * n.y,
                                  v.z + n_value * amplitude * n.z))
    mfnMesh.setPoints(newVerts, om.MSpace.kWorld)

# ----------------------------
# Run UI
# ----------------------------
create_mountain_ui()
