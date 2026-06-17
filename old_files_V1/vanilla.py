# global imports
import json
import math
import numpy as np
import os
import subprocess
import scipy.stats.qmc as qmc
import time
import matplotlib.pyplot as plt


def getConfig():
    # The dsParameterBounds names need to match the NX parameter names in the part file as well as the journal file!
    config_file = os.path.join(os.getcwd(), 'config.json')
    print(f"Loading configuration from: {config_file}")
    try:
        # Open and read the JSON file
        with open(config_file, 'r') as file:
            config = json.load(file)
        print("Configuration loaded successfully.")
    except Exception as e:
        print("Configuration file not found. Make sure it is in the same folder as the main.py script")
    return config

def calculate_edge_dist(sampleLst):
    
    r1 = 6
    r2 = 9
    a = 25/2
    b = 7.5

    #Circle 1
    x1 = sampleLst['x1']
    y1 = sampleLst['y1']
    d_circle1 = 30 - ( max( abs(x1), abs(y1)) + r1)  #nice! negative if out of bounds
    print("Distance Circle 1 to edge: ", d_circle1)

    #Circle 2
    x2 = sampleLst['x2']
    y2 = sampleLst['y2']
    d_circle2 = 30 - ( max( abs(x2), abs(y2)) + r2)
    print("Distance Circle 2 to edge: ", d_circle2)


    #Oval shape
    x3 = sampleLst['x3']
    y3 = sampleLst['y3']
    angle = sampleLst['angle']

    xh = x3 + math.sin(angle) * b
    yh = y3 + math.cos(angle) * b

    xstar1, ystar1 = x3 - math.cos(angle) * a,  y3 + math.cos(angle) * a
    xstar2, ystar2 = x3 + math.cos(angle) * a, y3 - math.cos(angle) * a
     
    #distance to circle 1
    d_oval_c1_11 = math.sqrt((x1-xstar1)**2+(y1-ystar1)**2) - r1 - b
    d_oval_c1_12 = math.sqrt((x1-xstar2)**2+(y1-ystar2)**2) - r1 - b
    d_oval_c1_2 = abs( (x3-xh)*math.sin(angle) - (y3-yh)*math.cos(angle))

    n = np.array([math.sin(angle), math.cos(angle)])
    v = np.array([(x3-xh), (y3-yh)])
    d_oval_c1_2test = abs(np.dot(v,n))

    print("Finding the distance for the following sample: ")
    print("x1  = ", x1)
    print("y1  = ", y1)
    print("x2  = ", x2)
    print("y2  = ", y2)
    print("x3  = ", x3)
    print("y3  = ", y3)
    print("angle  = ", angle)

    print("Distance Oval to Circle 1 (focal point 1): ", d_oval_c1_11)
    print("Distance Oval to Circle 1 (focal point 2): ", d_oval_c1_12)
    print("Distance Oval to Circle 1 (perpendicular): ", d_oval_c1_2)
    print("Distance Oval to Circle 1 (perpendicular test): ", d_oval_c1_2test)

    #distance to circle 2
    d_oval_c2_1 = math.sqrt((x1-x2)**2+(y1-y2)**2) - r1 - b
    d_oval_c2_2 = abs( (x3-xh)*math.sin(angle) - (y3-yh)*math.cos(angle))

def visualize_domain(show=True, ax=None, save_path=None, sample=None):
    """Plot a 60x60 square centered at (0,0).

    If sample (dict) is provided it should have the same keys as
    calculate_edge_dist: x1,y1,x2,y2,x3,y3,angle. The function will
    draw the two circles using centers (x1, y1) and (x2, y2) with
    radii 6 and 9, respectively, plus the rotated oval/ellipse.

    Returns (fig, ax).
    """
    import matplotlib.patches as patches

    if plt is None:
        print("matplotlib is not available, cannot visualize domain.")
        return None

    created_fig = False
    if ax is None:
        fig, ax = plt.subplots()
        created_fig = True
    else:
        fig = ax.figure

    half = 30
    # draw square
    rect = patches.Rectangle((-half, -half), 2 * half, 2 * half, fill=False, edgecolor='black')
    ax.add_patch(rect)
    # mark center
    ax.plot(0, 0, 'ro')

    # if sample provided, draw shapes
    if sample is not None:
        try:
            r1 = 6
            r2 = 9
            a = 25 / 2
            b = 7.5
            x1 = sample['x1']
            y1 = sample['y1']
            x2 = sample['x2']
            y2 = sample['y2']
            x3 = sample['x3']
            y3 = sample['y3']
            angle = sample['angle']

            c1 = patches.Circle((x1, y1), r1, fill=False, edgecolor='blue', label='Circle 1 (r=6)')
            c2 = patches.Circle((x2, y2), r2, fill=False, edgecolor='orange', label='Circle 2 (r=9)')
            # ellipse: width=2a, height=2b, angle in degrees
            ell = patches.Ellipse((x3, y3), width=2 * a, height=2 * b, angle=math.degrees(angle), fill=False, edgecolor='green')
            ax.add_patch(c1)
            ax.add_patch(c2)
            ax.add_patch(ell)
        except Exception:
            pass

    ax.set_xlim(-half - 5, half + 5)
    ax.set_ylim(-half - 5, half + 5)
    ax.set_aspect('equal', 'box')
    ax.grid(True)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_title('60x60 domain centered at (0,0)')
    if sample is not None:
        ax.legend(loc='upper right')

    if save_path:
        fig.savefig(save_path)
    if show and created_fig:
        plt.show()

    return fig, ax

def generateSamples(config, nSamples):
    """
    Generates Latin Hypercube samples for given parameters and saves each sample as a separate JSON file.
    
    Parameters:
    - parameters: dict, keys are parameter names and values are [min, max] lists
    - numSamples: int, number of samples to generate
    """
    # create one dictionary containing all parameters that have ranges
    parameters = config["dsParameterBounds"]

    # Generate input files for latin hypercube samples
    sampler = qmc.LatinHypercube(d=len(parameters)) 
    samples = sampler.random(nSamples)
    scaled_samples = qmc.scale(samples, [v[0] for v in parameters.values()], [v[1] for v in parameters.values()])
   
    #### HERE I COULD CHECK WHETHER THE SAMPLES ARE VALID (E.G. NOT OUT OF BOUNDS) AND RESAMPLE IF NECESSARY, BUT FOR NOW I JUST GENERATE N SAMPLES AND CHECK VALIDITY LATER IN THE FREECAD SCRIPT. THIS IS BECAUSE I MIGHT WANT TO USE AN OPTIMIZER THAT PROPOSES NEW SAMPLES BASED ON PREVIOUS EVALUATIONS, AND THEN I WOULD ALSO NEED TO CHECK THE VALIDITY OF THESE PROPOSED SAMPLES.
   
   
   
    sampleLst = []  # Format of each entry in sampleLst: {param1: value1, param2: value2, ...}
    for i in range(nSamples):
        param_dict = {k:float(v) for k,v in zip(parameters.keys(), scaled_samples[i])}
        sampleLst.append(param_dict)
    return sampleLst

def build_command(sample, journalFile, freeCadpath):
    freecad_exec_path = os.path.join(freeCadpath,  r"bin\freecadcmd.exe") # I changed this here because with 1.1 FREECADCMD is the name of the executable, not FreeCADCmd.exe. You might need to change this back if you have 1.0 installed 
    cmd = [freecad_exec_path, journalFile, json.dumps(sample),] 
    return cmd

def calculate_objective(sample, freeCAD_journal, freeCADpath):
    # create necessary folders
    # try processing the current sample geometry
    print(f"Loading files for sample: {sample}, freeCAD_journal: {freeCAD_journal}, freeCADpath: {freeCADpath}")
    try:
        # run freecad journal, that updates the geometry with current parameters
        # and solves the fe simulation and returns the deformation energy
        cmd = build_command(sample, freeCAD_journal , freeCADpath)
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)# creationflags=subprocess.CREATE_NO_WINDOW)
        assert res.returncode == 0 , "freeCAD script routine failed"
        # retrieve the absorbed energy from the logged string
        # make sure the last thing you log in the full_journal_fc.py script is the 
        absorbed_energy = float(res.stdout.split('\n')[-3])
        max_stress = float(res.stdout.split('\n')[-2])
    # catch exceptions and log failed samples. DB entry at index (sampleId) is invalid
    except Exception as e:
        print(f"Sample processing failed due to error: {e}")
        print(res.stdout)
        print(res.stderr)
        time.sleep(1)
        return None

    # return binary files for optional backward conversion to geometries
    return absorbed_energy, max_stress
    
def main():
    # """
    # In this example, a latin hypercube sampling is performed on the parameter bounds
    # and the geometries are evaluated for there objective of energy absorbtion. 
    # TODO:
    # Your task is to implement an optimizer to find the optimal geometry maximizing the
    # energy absorption capacity. This can include better sampling strategies, choosing 
    # a suitable optimizer and handling parameter combinations that yield invalid geometries.

    # Do not forget to fulfil the maximum stress constrain as well as the geometry 
    # constraints listed in section 2 of the project description.

    # """
    # # TODO: set the freecad path your the installation location of freeCAD
    # #
    # # freeCAD_path = r'C:/Program Files/FreeCAD 1.1'  # I have 1.1 installed
    # freeCAD_path = r'C:/Program Files/FreeCAD 1.0' # default on windows
    # if not os.path.exists(freeCAD_path):
    #     print(f"FreeCAD path does not exist: {freeCAD_path}")
    #     return


    # # freecad scripts for geometry manipulation and fem simulation
    # '''
    # if the script does not work initially, copy the full_journal_fc.py file
    # to the bin folder in the FreeCAD 1.0 directory,  i.e for windows default
    # 'C:/Program Files/FreeCAD 1.0/bin/full_journal_fc.py' and change the 
    # freeCAD_journal variable below to this path.
    # After running like that once, you should be able to copy the file back and
    # run normally.
    # '''
 
    # freeCAD_journal = os.path.join(os.getcwd(), "full_journal_fc.py")
    # #freeCAD_journal =  "C:/Program Files/FreeCAD 1.1/bin/full_journal_fc.py"
    # if not os.path.exists(freeCAD_journal):
    #     print(f"FreeCAD journal file not found: {freeCAD_journal}")
    #     return
    # print(f"Using freeCAD journal file at: {freeCAD_journal}")



    # generates latin hypercube samples of the parameters
    nSamples = 1

    print("Getting config....")
    config = getConfig()
   
    # samples is a list of dictionary containing parameter:value pairs
    samples = generateSamples(config, nSamples)  # has nothing to do with pathes and FreeCAD


    calculate_edge_dist(samples[0])  
    #try to visualize the domain (pass the first sample so circles/ellipse are drawn)
    visualize_domain(sample=samples[0])
    exit()

    results = []
    for sample in samples:
        absorbed_energy, max_stress = calculate_objective(sample, freeCAD_journal, freeCAD_path)
        if absorbed_energy is not None:
            sample['energy_objective'] = absorbed_energy
            sample['stress_constraint'] = max_stress
            results.append(sample)

    # each entry in the results list is a dictionary with cadparams:value pairs
    # as well as the objective:value pair corresponding to this geometry
    print(results)
    # print objective value of one result
    idx = 1
    print('objective value (total plastic deformation energy):', results[idx]['energy_objective'])
    print('maximum stress value:', results[idx]['stress_constraint'])



if __name__ == "__main__":
    main()