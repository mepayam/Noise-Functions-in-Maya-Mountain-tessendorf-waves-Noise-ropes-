import maya.cmds as cmds
import math
import random

# =============================
# Turbulent-like noise function
# =============================
def turbulent_noise(t, frequency=2.0, octaves=3, seed=0):
    """Simulate turbulent noise using sine waves + small random variations"""
    random.seed(seed)
    value = 0.0
    amplitude = 1.0
    for i in range(octaves):
        phase = random.random() * 2 * math.pi
        value += math.sin(2 * math.pi * t * frequency * (i+1) + phase) * amplitude
        amplitude *= 0.5
    return value

# =============================
# UI
# =============================
def create_turbulent_noise_ui():
    win_name = "turbulentNoiseUI"
    
    if cmds.window(win_name, exists=True):
        cmds.deleteUI(win_name)
    
    cmds.window(win_name, title="3D Turbulent Noise Animator", widthHeight=(400, 450))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnAlign="center")
    
    # Object selection
    cmds.text(label="Select Object:")
    obj_field = cmds.textFieldButtonGrp('objField', buttonLabel='Get Selected', text='')
    
    def get_selected(*args):
        sel = cmds.ls(selection=True)
        if sel:
            cmds.textFieldButtonGrp(obj_field, edit=True, text=sel[0])
        else:
            cmds.warning("No object selected!")
    
    cmds.textFieldButtonGrp(obj_field, edit=True, buttonCommand=get_selected)
    
    # Frame sliders
    cmds.text(label="Start Frame:")
    min_frame_slider = cmds.intSliderGrp('minFrame', field=True, minValue=1, maxValue=1000, value=1)
    
    cmds.text(label="End Frame:")
    max_frame_slider = cmds.intSliderGrp('maxFrame', field=True, minValue=1, maxValue=1000, value=120)
    
    # Distance / amplitude
    cmds.text(label="Distance (Amplitude):")
    distance_slider = cmds.floatSliderGrp('distanceSlider', field=True, minValue=0.1, maxValue=50, value=5)
    
    # Frequency
    cmds.text(label="Frequency:")
    freq_slider = cmds.floatSliderGrp('freqSlider', field=True, minValue=0.1, maxValue=10, value=2)
    
    # Noise Offset
    cmds.text(label="Noise Offset:")
    offset_slider = cmds.floatSliderGrp('offsetSlider', field=True, minValue=0.0, maxValue=10.0, value=0.5)
    
    # Seed
    cmds.text(label="Random Seed:")
    seed_slider = cmds.intSliderGrp('seedSlider', field=True, minValue=0, maxValue=9999, value=42)
    
    # Apply button
    def apply_noise(*args):
        obj = cmds.textFieldButtonGrp(obj_field, query=True, text=True)
        if not cmds.objExists(obj):
            cmds.warning("Object does not exist!")
            return
        
        start_frame = cmds.intSliderGrp(min_frame_slider, query=True, value=True)
        end_frame = cmds.intSliderGrp(max_frame_slider, query=True, value=True)
        amplitude = cmds.floatSliderGrp(distance_slider, query=True, value=True)
        frequency = cmds.floatSliderGrp(freq_slider, query=True, value=True)
        offset_control = cmds.floatSliderGrp(offset_slider, query=True, value=True)
        seed = cmds.intSliderGrp(seed_slider, query=True, value=True)
        
        # Store original position and apply random initial offset
        orig_pos = cmds.xform(obj, query=True, worldSpace=True, translation=True)
        init_offset = [random.uniform(-amplitude, amplitude) for _ in range(3)]
        base_pos = [orig_pos[i] + init_offset[i] for i in range(3)]
        
        for frame in range(start_frame, end_frame + 1):
            t = float(frame - start_frame) / (end_frame - start_frame)
            noise_x = base_pos[0] + turbulent_noise(t + offset_control, frequency, octaves=3, seed=seed) * amplitude
            noise_y = base_pos[1] + turbulent_noise(t + offset_control + 0.33, frequency, octaves=3, seed=seed+1) * amplitude
            noise_z = base_pos[2] + turbulent_noise(t + offset_control + 0.66, frequency, octaves=3, seed=seed+2) * amplitude
            
            cmds.setKeyframe(obj, attribute="translateX", value=noise_x, t=frame)
            cmds.setKeyframe(obj, attribute="translateY", value=noise_y, t=frame)
            cmds.setKeyframe(obj, attribute="translateZ", value=noise_z, t=frame)
        
        print(f"Turbulent-like noise applied to {obj} from frame {start_frame} to {end_frame}")
    
    cmds.button(label="Apply Turbulent Noise Animation", command=apply_noise)
    cmds.showWindow(win_name)

# Run UI
create_turbulent_noise_ui()
