# global imports
import json
import math
import numpy as np
import os
import subprocess
import scipy.stats.qmc as qmc
import time
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF


def getConfig():
    # The dsParameterBounds names need to match the NX parameter names in the part file as well as the journal file!
    #config_file = os.path.join(os.getcwd(), 'config.json')
    config_file = os.path.join(os.getcwd(), 'config.json')          #DEBUG CONFIG
    #print(f"Loading configuration from: {config_file}")
    try:
        # Open and read the JSON file
        with open(config_file, 'r') as file:
            config = json.load(file)
        print("Configuration loaded successfully.")
    except Exception as e:
        print("Configuration file not found. Make sure it is in the same folder as the main.py script")
    return config

def train_absorbed_energy_gp(x_train, y_train_ae):
    """This function trains a GP model for the absorbed energy for later Bayesian optimization"""

    print("Training GP for absorbed energy")
    kernel = 1 * RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e2))
    gp_absorbed_energy = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=9, normalize_y=True)
    gp_absorbed_energy.fit(x_train, y_train_ae)
    print("Training done\n GP absorbed energy: ", gp_absorbed_energy.kernel_)   #shows the kernel after hyperparam optimization
    return gp_absorbed_energy

def train_max_stress_gp(x_train, y_train_ms):
    """This function trains a GP model for the maximum stress for later Bayesian optimization"""

    print("Training GP for maximum stress")
    kernel = 1 * RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e2))
    gp_max_stress = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=9, normalize_y=True)
    gp_max_stress.fit(x_train, y_train_ms)
    print("Training done\n GP max stress: ", gp_max_stress.kernel_)
    return gp_max_stress

def calculate_edge_dist(sampleLst, r1, r2, a, b):
    """This function is used to calculate the edge distance of all 3 object and check if it is okay. 
     Returns True if edge distance constraint is fulfilled, False otherwise"""
    
    half_square_length = 30
    square_length = 60
    clearance = 2

    #This code here is useless now with v2, as the coordinate system changed. As I can fulfill the edge distance constraints of the circles 
    #with the config already though I will just comment out this code snippet here

    #Circle 1
    # x1 = sampleLst['x1']
    # y1 = sampleLst['y1']
    # d_circle1 = half_square_length - ( max( abs(x1), abs(y1)) + r1)
    #print("Distance Circle 1 to edge: ", d_circle1)

    #Circle 2
    # x2 = - sampleLst['x2']              # HAD TO FIX THESE TO BE CONSISTENT WITH DEFINITON IN FREECAD FILE
    # y2 = sampleLst['y2']
    # d_circle2 = half_square_length - ( max( abs(x2), abs(y2)) + r2)
    #print("Distance Circle 2 to edge: ", d_circle2)

    #Oval Shape 
    x3 =  sampleLst['x3']           
    y3 =  sampleLst['y3']
    angle = sampleLst["angle"]
    angle = math.radians(angle)
  
    x_oval_1 = x3 + math.cos(angle) * a + b
    x_oval_2 = x3 - math.cos(angle) * a - b
    x_oval_3 = x3 + math.cos(angle) * a - b
    x_oval_4= x3 - math.cos(angle) * a + b

    x_oval_max = max( (x_oval_1), (x_oval_2), (x_oval_3), (x_oval_4))
    x_oval_min = min( (x_oval_1), (x_oval_2), (x_oval_3), (x_oval_4))

    y_oval_1 = y3 + math.sin(angle) * a + b
    y_oval_2 = y3 - math.sin(angle) * a - b
    y_oval_3 = y3 + math.sin(angle) * a - b
    y_oval_4 = y3 - math.sin(angle) * a + b

    y_oval_max = max( (y_oval_1), (y_oval_2), (y_oval_3), (y_oval_4))
    y_oval_min = min( (y_oval_1), (y_oval_2), (y_oval_3), (y_oval_4))

    d_oval_max = square_length - max( x_oval_max, y_oval_max)
    d_oval_min = min( x_oval_min, y_oval_min)
    #print("Distance oval to edge: ", d_oval)

    #print("Edge distance summary: \n", )
    #print(f"Circle 1  {x1, y1}:  ", d_circle1, d_circle1>clearance)
    #print(f"Circle 2  {x2, y2}:  ", d_circle2, d_circle2>clearance)
    #print(f"Oval  {x3, y3, angle}:  ", d_oval, d_oval>clearance) 

    return (d_oval_max>clearance) & (d_oval_min>clearance) #(d_circle1 > clearance) & (d_circle2>clearance) & (d_oval>clearance)

def calculate_circle_oval_dist(x_c, y_c, r_c, x_o, y_o, angle, a, b):
   #This function calculates the distance between a circle and the oval shape. Used as a helper later in calculate_object_dist()"""

    theta = -angle

    # circle center relative to oval center
    dx = x_c - x_o
    dy = y_c - y_o

    # transform circle center into oval-local coordinates
    # u = along oval centerline
    # v = perpendicular to oval centerline
    u =  math.cos(theta) * dx + math.sin(theta) * dy
    v = -math.sin(theta) * dx + math.cos(theta) * dy

    if u < -a:
        # closest to left semicircle center (-a, 0)
        center_dist = math.hypot(u + a, v)

    elif u > a:
        # closest to right semicircle center (a, 0)
        center_dist = math.hypot(u - a, v)

    else:
        # closest to straight middle section
        center_dist = abs(v)

    return center_dist - b - r_c

def calculate_object_dist(sampleLst, r1, r2, a, b):
    #This function calculates the distance between the two circles and the oval shape. It returns True if all distances are greater than a specified cutout distance, False otherwise.
    cutout_dist = 1

    x1 = sampleLst['x1']
    y1 = sampleLst['y1']
    x2 = sampleLst['x2']   
    y2 = sampleLst['y2']
    x3 = sampleLst['x3']
    y3 = sampleLst['y3']
    angle = sampleLst["angle"]
    angle = math.radians(angle)

    circle_dist = math.sqrt( (x1-x2)**2 + (y1-y2)**2) - r1 - r2

    #CALCULATE DISTANCES BETWEEN OBJECTS
    #Oval shape

    # xG1, yG1 = x3 + math.sin(angle) * b, y3 + math.cos(angle) * b               #upper
    # xG2, yG2 = x3 - math.sin(angle) * b, y3 - math.cos(angle) * b               #lower

    # xstar1, ystar1 = x3 - math.cos(angle) * a,  y3 + math.sin(angle) * a        # to the left
    # xstar2, ystar2 = x3 + math.cos(angle) * a, y3 - math.sin(angle) * a         # to the right
     
    #distance to circle 1
    #d_oval_c1_11 = math.sqrt((x1-xstar1)**2+(y1-ystar1)**2) - r1 - b            # distance to the half-circle left
    #d_oval_c1_12 = math.sqrt((x1-xstar2)**2+(y1-ystar2)**2) - r1 - b            # distance to the half-circle right
    

    # n = np.array([math.sin(angle), math.cos(angle)])
    # v1_1 = np.array([(x1-xG1), (y1-yG1)])
    # v1_2 = np.array([(x1-xG2), (y1-yG2)])
    # d_oval_c1_21 = abs(np.dot(v1_1,n)) - r1
    # d_oval_c1_22 = abs(np.dot(v1_2,n)) - r1

    #DEBUG
    #print("d_oval_c1_11", d_oval_c1_11)
    #print("d_oval_c1_12", d_oval_c1_12)
    #print("d_oval_c1_21", d_oval_c1_21)
    #print("d_oval_c1_22", d_oval_c1_22)

    #circ1_oval_dist = min(d_oval_c1_11, d_oval_c1_12, d_oval_c1_21, d_oval_c1_22)
    circ1_oval_dist = calculate_circle_oval_dist(x1, y1, r1,x3, y3, angle, a, b)

    #distance to circle 2
    #d_oval_c2_11 = math.sqrt((x2-xstar1)**2+(y2-ystar1)**2) - r2 - b            # distance to the half-circle left
    #d_oval_c2_12 = math.sqrt((x2-xstar2)**2+(y2-ystar2)**2) - r2 - b            # distance to the half-circle right
    
    # n = np.array([math.sin(angle), math.cos(angle)])
    # v2_1 = np.array([(x2-xG1), (y2-yG1)])
    # v2_2 = np.array([(x2-xG2), (y2-yG2)])
    # d_oval_c2_21 = abs(np.dot(v2_1,n)) - r2
    # d_oval_c2_22 = abs(np.dot(v2_2,n)) - r2

    # circ2_oval_dist = min(d_oval_c2_11, d_oval_c2_12, d_oval_c2_21, d_oval_c2_22)
    circ2_oval_dist = calculate_circle_oval_dist( x2, y2, r2,x3, y3, angle, a, b)

    #print("Distance between circles: ", circle_dist)
    #print("Distance between circle 1 and oval: ", circ1_oval_dist)
    #print("Distance between circle 2 and oval: ", circ2_oval_dist)

    return (circle_dist > cutout_dist) & (circ1_oval_dist > cutout_dist) & (circ2_oval_dist > cutout_dist)

def get_valid_samples(samples, r1, r2, a, b):
    
    valid_samples = []
    for sample in samples:
        check_edge_dist = calculate_edge_dist(sample, r1, r2, a, b)  
        check_cutout_dist = calculate_object_dist(sample, r1, r2, a, b)

        #print("Edge distance constraint: ", check_edge_dist)
        #print("Cutout distance constraint: ", check_cutout_dist)

        sample_validity_check = check_edge_dist and check_cutout_dist  
        #print("Valid sample? ", sample_validity_check)

        if sample_validity_check == True:           #Stupid bug before here, where I removed invalid samples but messed up somehow ordering of list
            valid_samples.append(sample)

    return valid_samples

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
            r1 = 9
            r2 = 6
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
    sampleLst = []  # Format of each entry in sampleLst: {param1: value1, param2: value2, ...}

    for i in range(nSamples):
        param_dict = {k:float(v) for k,v in zip(parameters.keys(), scaled_samples[i])}
        sampleLst.append(param_dict)

    return sampleLst

def build_command(sample, journalFile, freeCadExecpath):
    cmd = [freeCadExecpath, journalFile, json.dumps(sample),] 
    return cmd

def calculate_objective(sample, freeCAD_journal, freeCADExecPath):
    # create necessary folders
    # try processing the current sample geometry
    print(f"\nLoading files for sample: {sample}, freeCAD_journal: {freeCAD_journal}, freeCADExecPath: {freeCADExecPath}\n")
    try:
        # run freecad journal, that updates the geometry with current parameters
        # and solves the fe simulation and returns the deformation energy
        cmd = build_command(sample, freeCAD_journal , freeCADExecPath)
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)# creationflags=subprocess.CREATE_NO_WINDOW)
        assert res.returncode == 0 , "freeCAD script routine failed"
        # retrieve the absorbed energy from the logged string
        # make sure the last thing you log in the full_journal_fc.py script is the 
        absorbed_energy = float(res.stdout.split('\n')[-3])
        max_stress = float(res.stdout.split('\n')[-2])
        if "Access violation" in res.stderr:
            raise Exception("Access violation error in freeCAD script, likely due to invalid geometry or failed meshing.")
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
    """
    In this example, a latin hypercube sampling is performed on the parameter bounds
    and the geometries are evaluated for there objective of energy absorbtion. 
    TODO:
    Your task is to implement an optimizer to find the optimal geometry maximizing the
    energy absorption capacity. This can include better sampling strategies, choosing 
    a suitable optimizer and handling parameter combinations that yield invalid geometries.

    Do not forget to fulfil the maximum stress constrain as well as the geometry 
    constraints listed in section 2 of the project description.

    """
    # freeCAD_path = r'C:/Program Files/FreeCAD 1.1'  # I have 1.1 installed
    freeCADExecPath = r'C:/Program Files/FreeCAD 1.0/bin/FreeCADCmd.exe' # default on windows
    if not os.path.exists(freeCADExecPath):
        print(f"FreeCAD executable path does not exist: {freeCADExecPath}")
        return

    # freecad scripts for geometry manipulation and fem simulation
    '''
    if the script does not work initially, copy the full_journal_fc.py file
    to the bin folder in the FreeCAD 1.0 directory,  i.e for windows default
    'C:/Program Files/FreeCAD 1.0/bin/full_journal_fc.py' and change the 
    freeCAD_journal variable below to this path.
    After running like that once, you should be able to copy the file back and
    run normally.
    '''
 
    freeCAD_journal = os.path.join(os.getcwd(), "full_journal_fc.py")
    #freeCAD_journal =  "C:/Program Files/FreeCAD 1.1/bin/full_journal_fc.py"
    if not os.path.exists(freeCAD_journal):
        print(f"FreeCAD journal file not found: {freeCAD_journal}")
        return
    print(f"Using freeCAD journal file at: {freeCAD_journal}")

    'GEOMETRY DEFINITION'
    r1 = 9
    r2 = 6
    a = 25/2
    b = 7.5 #radius of the oval shape

    'CONSTRAINT'
    max_stress_constraint = 275.0

    # generates latin hypercube samples of the parameters
    nSamples = 45   # Low number just for testing, for data generation I increased this by quite a lot, as many results get filtered

    #print("Getting config....")
    config = getConfig()
   
    # samples is a list of dictionary containing parameter:value pairs
    samples = generateSamples(config, nSamples)  # has nothing to do with paths and FreeCAD

    valid_samples = get_valid_samples(samples, r1, r2, a, b)
    
    samples = valid_samples
    print(f"After checking for validity, there are {len(samples)} left")

    #try to visualize the domain (pass the first sample so circles/ellipse are drawn)
    #visualize_domain(sample=samples[0])

    #exit()

    results = []
    max_absorded_energy = 0
    max_stress_sample = 0
    index_best_sample = 0


    'FOR OPTIMIZATION WE NEED A SURROGATE MODEL'
    ''
    'FIRST IDEA: USE GAUSSIAN PROCESSES TO LEARN A SURROGATE MODEL OF THE ABSORBED ENERGY AND '

    feature_names = ["x1", "y1", "x2", "y2", "x3", "y3", "angle"]
    x_train = []
    y_train_ae = []     # absorbed energy
    y_train_ms = []     # max stress


    for i, sample in enumerate(samples):
        absorbed_energy, max_stress = calculate_objective(sample, freeCAD_journal, freeCADExecPath)
        if absorbed_energy is not None:
            print(f"Sample {sample} -> Absorbed Energy: {absorbed_energy}, Max Stress: {max_stress}")
            sample['energy_objective'] = absorbed_energy
            sample['stress_constraint'] = max_stress
            results.append(sample)
        
        if max_stress < max_stress_constraint:
            if absorbed_energy > max_absorded_energy:
                max_absorded_energy = absorbed_energy 
                max_stress_sample = max_stress
                index_best_sample = i

        'HERE COMES INPUT FOR GP LEARNING'
        x_train.append([sample[name] for name in feature_names])
        y_train_ae.append(absorbed_energy)      #[sample["energy_objective"]]
        y_train_ms.append(max_stress)
        
    
    #gp_absorbed_energy = train_absorbed_energy_gp(x_train, y_train_ae)    #TRAIN MODEL FOR ABSORBED ENERGY
   # gp_max_stress = train_max_stress_gp(x_train, y_train_ms)         #TRAIN MODEL FOR MAX STRESS
    
    #print("\nresults", results)
    # each entry in the results list is a dictionary with cadparams:value pairs
    # as well as the objective:value pair corresponding to this geometry
    
    # print objective value of one result
    # idx = 1
    # print('objective value (total plastic deformation energy):', results[idx]['energy_objective'])
    # print('maximum stress value:', results[idx]['stress_constraint'])

    print('max objective value (total plastic deformation energy):', max_absorded_energy )
    print('maximum stress value:', max_stress_sample)
    print(f"This was recorded for sample {index_best_sample} with the following parameters {samples[index_best_sample]}")

    # Save best result to results.csv file with added datestamp
    csv_path = Path("results.csv")
    new_result = samples[index_best_sample]
    new_result["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pd.DataFrame([new_result]).to_csv(csv_path,mode="a",header=not csv_path.exists(),index=False)

    # Save all results to all_results.csv file with added datestamp
    csv_path_all_results = Path("all_results.csv")

    for result in results:
        result["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pd.DataFrame(results).to_csv(csv_path_all_results,mode="a",header=not csv_path_all_results.exists(),index=False)
    
    # whats's missing: after training GPs for max stress and absorbed energy, we need a sampling strategy = aquisition function 
    # this should then be used to sample new geometries, make on-line update of the surrogate model until we find the optimal geometry.

    #Implementing GP training from file in new python file gp_predict.py. This file is also used for all the remaining tasks
    

if __name__ == "__main__":
    main()