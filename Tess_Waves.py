import maya.cmds as cmds
import maya.api.OpenMaya as om
import math
import random

def phillips_spectrum(kx, kz, wind_speed, wind_dir_x, wind_dir_z, gravity=9.81):
    """
    Phillips Spectrum - core of Tessendorf algorithm
    Describes the statistical distribution of ocean wave energy
    
    P(k) = A * exp(-1/(kL)^2) / k^4 * |k·w|^2
    """
    k_length = math.sqrt(kx*kx + kz*kz)
    
    if k_length < 0.0001:
        return 0.0
    
    # Largest wave from wind
    L = (wind_speed * wind_speed) / gravity
    
    # Normalize wind direction
    wind_length = math.sqrt(wind_dir_x*wind_dir_x + wind_dir_z*wind_dir_z)
    if wind_length < 0.0001:
        wind_dir_x, wind_dir_z = 1.0, 0.0
        wind_length = 1.0
    
    wx = wind_dir_x / wind_length
    wz = wind_dir_z / wind_length
    
    # k dot w (wave alignment with wind)
    k_dot_w = (kx * wx + kz * wz) / k_length
    
    # Amplitude constant
    A = 0.0081
    
    # Suppress waves moving opposite to wind
    if k_dot_w < 0.0:
        k_dot_w = 0.0
    
    # Phillips spectrum formula
    k_length_2 = k_length * k_length
    k_length_4 = k_length_2 * k_length_2
    
    kL = k_length * L
    
    # Exponential suppression for small waves
    exp_term = math.exp(-1.0 / (kL * kL))
    
    # Suppress very small waves
    l_small = L / 1000.0
    exp_term *= math.exp(-k_length_2 * l_small * l_small)
    
    # Final spectrum
    phillips = A * exp_term / k_length_4 * (k_dot_w * k_dot_w)
    
    return phillips

def tessendorf_displacement(x, z, time, resolution, patch_size, wind_speed,
                           wind_dir_x, wind_dir_z, wave_amplitude, choppiness, seed=42):
    """
    Calculate Tessendorf ocean displacement for a single point
    Returns: (height, displacement_x, displacement_z)
    """
    height = 0.0
    displacement_x = 0.0
    displacement_z = 0.0
    
    # Wave number resolution
    dk = 2.0 * math.pi / patch_size
    
    # Set seed for consistent randomness
    random.seed(seed)
    
    # Sum contributions from wave vectors
    for nx in range(-resolution//2, resolution//2):
        for nz in range(-resolution//2, resolution//2):
            if nx == 0 and nz == 0:
                continue
            
            # Wave vector k
            kx = nx * dk
            kz = nz * dk
            k_length = math.sqrt(kx*kx + kz*kz)
            
            if k_length < 0.0001:
                continue
            
            # Phillips spectrum
            P_k = phillips_spectrum(kx, kz, wind_speed, wind_dir_x, wind_dir_z)
            
            # Gaussian random with Phillips spectrum
            h0_real = random.gauss(0, 1) * math.sqrt(P_k * 0.5)
            h0_imag = random.gauss(0, 1) * math.sqrt(P_k * 0.5)
            
            # Dispersion relation: ω = sqrt(g*k)
            omega = math.sqrt(9.81 * k_length)
            
            # Time evolution
            phase = omega * time
            cos_phase = math.cos(phase)
            sin_phase = math.sin(phase)
            
            # Complex multiplication
            ht_real = h0_real * cos_phase - h0_imag * sin_phase
            ht_imag = h0_real * sin_phase + h0_imag * cos_phase
            
            # Spatial phase: k·x
            spatial_phase = kx * x + kz * z
            cos_spatial = math.cos(spatial_phase)
            sin_spatial = math.sin(spatial_phase)
            
            # Wave contribution
            wave_contribution = (ht_real * cos_spatial - ht_imag * sin_spatial) * wave_amplitude
            
            height += wave_contribution
            
            # Choppiness (horizontal displacement)
            if k_length > 0.0001:
                displacement_x += -choppiness * (kx / k_length) * wave_contribution
                displacement_z += -choppiness * (kz / k_length) * wave_contribution
    
    return height, displacement_x, displacement_z

def apply_tessendorf_to_mesh(obj_name, resolution=8, patch_size=100.0,
                             wind_speed=15.0, wind_dir_x=1.0, wind_dir_z=0.0,
                             wave_amplitude=1.0, choppiness=1.0, time_value=0.0, seed=42):
    """
    Apply Tessendorf ocean deformation directly to mesh vertices
    """
    
    if not cmds.objExists(obj_name):
        cmds.warning(f"Object {obj_name} does not exist!")
        return False
    
    # Get mesh shape
    shapes = cmds.listRelatives(obj_name, shapes=True, fullPath=True)
    if not shapes:
        cmds.warning(f"{obj_name} has no shape!")
        return False
    
    shape = shapes[0]
    
    if cmds.nodeType(shape) != 'mesh':
        cmds.warning(f"{obj_name} is not a polygon mesh!")
        return False
    
    # Store original positions if not already stored
    if not cmds.attributeQuery('originalPositions', node=obj_name, exists=True):
        # Get current vertex positions and store them
        num_verts = cmds.polyEvaluate(obj_name, vertex=True)
        orig_positions = []
        
        for i in range(num_verts):
            pos = cmds.xform(f"{obj_name}.vtx[{i}]", query=True, translation=True, worldSpace=True)
            orig_positions.append(pos)
        
        # Store as string attribute
        cmds.addAttr(obj_name, longName='originalPositions', dataType='string')
        pos_string = str(orig_positions)
        cmds.setAttr(f"{obj_name}.originalPositions", pos_string, type='string')
    
    # Get original positions
    pos_string = cmds.getAttr(f"{obj_name}.originalPositions")
    original_positions = eval(pos_string)
    
    # Get bounding box for normalization
    bbox = cmds.exactWorldBoundingBox(obj_name)
    obj_width = bbox[3] - bbox[0]
    obj_depth = bbox[5] - bbox[2]
    center_x = (bbox[0] + bbox[3]) / 2.0
    center_z = (bbox[2] + bbox[5]) / 2.0
    
    print("Applying Tessendorf ocean directly to vertices...")
    print(f"Vertices: {len(original_positions)}")
    print(f"Resolution: {resolution}x{resolution}")
    print(f"Wind Speed: {wind_speed} m/s")
    
    # Apply displacement to each vertex
    num_verts = len(original_positions)
    
    for i in range(num_verts):
        # Get original position
        orig_x, orig_y, orig_z = original_positions[i]
        
        # Normalize to ocean patch coordinates
        ocean_x = ((orig_x - center_x) / obj_width) * patch_size
        ocean_z = ((orig_z - center_z) / obj_depth) * patch_size
        
        # Calculate Tessendorf displacement
        height, disp_x, disp_z = tessendorf_displacement(
            ocean_x, ocean_z, time_value, resolution, patch_size,
            wind_speed, wind_dir_x, wind_dir_z, wave_amplitude, choppiness, seed
        )
        
        # Apply displacement to original position
        new_x = orig_x + disp_x
        new_y = orig_y + height
        new_z = orig_z + disp_z
        
        # Set new vertex position
        cmds.xform(f"{obj_name}.vtx[{i}]", translation=[new_x, new_y, new_z], worldSpace=True)
    
    print(f"Tessendorf ocean applied to {num_verts} vertices!")
    return True

def reset_mesh_to_original(obj_name):
    """
    Reset mesh to original positions
    """
    if not cmds.objExists(obj_name):
        return False
    
    if not cmds.attributeQuery('originalPositions', node=obj_name, exists=True):
        cmds.warning("No original positions stored!")
        return False
    
    # Get original positions
    pos_string = cmds.getAttr(f"{obj_name}.originalPositions")
    original_positions = eval(pos_string)
    
    # Restore positions
    for i, pos in enumerate(original_positions):
        cmds.xform(f"{obj_name}.vtx[{i}]", translation=pos, worldSpace=True)
    
    print(f"Mesh reset to original shape")
    return True

def apply_deformer_from_ui(*args):
    """Apply Tessendorf deformation from UI"""
    obj_text = cmds.textField('selectedObjField', query=True, text=True)
    
    if not obj_text or obj_text == "None":
        cmds.confirmDialog(title='No Object',
                          message='Please select a mesh object first!',
                          button=['OK'])
        return
    
    # Get parameters
    resolution = int(cmds.intSliderGrp('resolutionSlider', query=True, value=True))
    patch_size = cmds.floatSliderGrp('patchSizeSlider', query=True, value=True)
    wind_speed = cmds.floatSliderGrp('windSpeedSlider', query=True, value=True)
    wind_dir_x = cmds.floatSliderGrp('windDirXSlider', query=True, value=True)
    wind_dir_z = cmds.floatSliderGrp('windDirZSlider', query=True, value=True)
    wave_amplitude = cmds.floatSliderGrp('amplitudeSlider', query=True, value=True)
    choppiness = cmds.floatSliderGrp('choppinessSlider', query=True, value=True)
    time_value = cmds.floatSliderGrp('timeSlider', query=True, value=True)
    seed = int(cmds.intSliderGrp('seedSlider', query=True, value=True))
    
    # Apply deformation
    apply_tessendorf_to_mesh(obj_text, resolution, patch_size,
                            wind_speed, wind_dir_x, wind_dir_z,
                            wave_amplitude, choppiness, time_value, seed)

def reset_mesh_from_ui(*args):
    """Reset mesh from UI"""
    obj_text = cmds.textField('selectedObjField', query=True, text=True)
    
    if obj_text and obj_text != "None":
        reset_mesh_to_original(obj_text)
    else:
        cmds.confirmDialog(title='No Object',
                          message='No object selected!',
                          button=['OK'])

def update_selection(*args):
    """Update selected object field"""
    selection = cmds.ls(selection=True)
    if selection:
        cmds.textField('selectedObjField', edit=True, text=selection[0])
    else:
        cmds.textField('selectedObjField', edit=True, text="None")

def create_test_plane(*args):
    """Create a test plane for ocean simulation"""
    plane = cmds.polyPlane(width=50, height=50, subdivisionsX=40, subdivisionsY=40, name="ocean_plane")
    cmds.select(plane[0])
    update_selection()
    cmds.confirmDialog(title='Test Plane Created',
                      message='Ocean test plane created with 40x40 subdivisions.\nReady to apply Tessendorf waves!',
                      button=['OK'])

def create_tessendorf_ui():
    """Create Tessendorf ocean UI"""
    window_name = "tessendorfOceanUI"
    
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
    
    window = cmds.window(window_name, title="Tessendorf Ocean - Direct Vertex Deformation",
                        widthHeight=(500, 750))
    
    main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=8,
                                   columnAttach=('both', 10))
    
    cmds.separator(height=10, style='none')
    cmds.text(label="Tessendorf Ocean Wave Deformer",
             font="boldLabelFont", align='center')
    cmds.text(label="Direct vertex displacement - No lattice!",
             font='smallPlainLabelFont', align='center')
    cmds.separator(height=15, style='in')
    
    # Object selection
    cmds.text(label="1. Select Mesh Object", font="boldLabelFont", align='left')
    
    obj_row = cmds.rowLayout(numberOfColumns=3,
                            columnWidth3=(260, 90, 90),
                            columnAttach=[(1, 'both', 0), (2, 'both', 2), (3, 'both', 2)])
    cmds.textField('selectedObjField', text="None", editable=False,
                  backgroundColor=[0.2, 0.2, 0.2])
    cmds.button(label='Get Selected', command=update_selection,
               backgroundColor=[0.4, 0.4, 0.5])
    cmds.button(label='Create Test', command=create_test_plane,
               backgroundColor=[0.3, 0.5, 0.3])
    cmds.setParent('..')
    
    cmds.separator(height=10, style='none')
    cmds.text(label="2. Ocean Parameters", font="boldLabelFont", align='left')
    
    # Resolution
    cmds.intSliderGrp('resolutionSlider',
                     label='Wave Resolution',
                     field=True,
                     minValue=4,
                     maxValue=20,
                     value=8,
                     columnWidth3=[160, 50, 180])
    
    # Patch size
    cmds.floatSliderGrp('patchSizeSlider',
                       label='Patch Size (m)',
                       field=True,
                       minValue=10.0,
                       maxValue=500.0,
                       value=100.0,
                       precision=1,
                       columnWidth3=[160, 50, 180])
    
    cmds.separator(height=10, style='none')
    cmds.text(label="3. Wind Parameters", font="boldLabelFont", align='left')
    
    # Wind speed
    cmds.floatSliderGrp('windSpeedSlider',
                       label='Wind Speed (m/s)',
                       field=True,
                       minValue=1.0,
                       maxValue=40.0,
                       value=15.0,
                       precision=1,
                       columnWidth3=[160, 50, 180])
    
    # Wind direction X
    cmds.floatSliderGrp('windDirXSlider',
                       label='Wind Direction X',
                       field=True,
                       minValue=-1.0,
                       maxValue=1.0,
                       value=1.0,
                       precision=2,
                       columnWidth3=[160, 50, 180])
    
    # Wind direction Z
    cmds.floatSliderGrp('windDirZSlider',
                       label='Wind Direction Z',
                       field=True,
                       minValue=-1.0,
                       maxValue=1.0,
                       value=0.0,
                       precision=2,
                       columnWidth3=[160, 50, 180])
    
    cmds.separator(height=10, style='none')
    cmds.text(label="4. Wave Shape", font="boldLabelFont", align='left')
    
    # Wave amplitude
    cmds.floatSliderGrp('amplitudeSlider',
                       label='Wave Height',
                       field=True,
                       minValue=0.1,
                       maxValue=5.0,
                       value=1.0,
                       precision=2,
                       columnWidth3=[160, 50, 180])
    
    # Choppiness
    cmds.floatSliderGrp('choppinessSlider',
                       label='Choppiness',
                       field=True,
                       minValue=0.0,
                       maxValue=3.0,
                       value=1.0,
                       precision=2,
                       columnWidth3=[160, 50, 180])
    
    cmds.separator(height=10, style='none')
    cmds.text(label="5. Animation & Variation", font="boldLabelFont", align='left')
    
    # Time
    cmds.floatSliderGrp('timeSlider',
                       label='Time Value',
                       field=True,
                       minValue=0.0,
                       maxValue=20.0,
                       value=0.0,
                       precision=2,
                       columnWidth3=[160, 50, 180])
    
    # Random seed
    cmds.intSliderGrp('seedSlider',
                     label='Random Seed',
                     field=True,
                     minValue=1,
                     maxValue=999,
                     value=42,
                     columnWidth3=[160, 50, 180])
    
    cmds.separator(height=15, style='in')
    
    # Action buttons
    button_row = cmds.rowLayout(numberOfColumns=2,
                                columnWidth2=(235, 235),
                                columnAttach=[(1, 'both', 2), (2, 'both', 2)])
    
    cmds.button(label='Apply Ocean Waves',
               command=apply_deformer_from_ui,
               height=40,
               backgroundColor=[0.2, 0.4, 0.5])
    
    cmds.button(label='Reset to Original',
               command=reset_mesh_from_ui,
               height=40,
               backgroundColor=[0.5, 0.3, 0.3])
    
    cmds.setParent('..')
    
    cmds.separator(height=10, style='none')
    
    cmds.showWindow(window)

# Launch UI
if __name__ == "__main__":
    create_tessendorf_ui()