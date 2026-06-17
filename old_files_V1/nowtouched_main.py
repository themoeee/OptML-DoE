# global imports
import json
import math
import numpy as np
import os
import subprocess
import scipy.stats.qmc as qmc
import time

def getConfig():
    # The dsParameterBounds names need to match the NX parameter names in the part file as well as the journal file!
    config_file = os.path.join(os.getcwd(), 'debug_config.json')
    try:
        # Open and read the JSON file
        with open(config_file, 'r') as file:
            config = json.load(file)
    except Exception as e:
        print("Configuration file not found. Make sure it is in the same folder as the main.py script")
    return config

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
    sampleLst = []
    for i in range(nSamples):
        param_dict = {k:float(v) for k,v in zip(parameters.keys(), scaled_samples[i])}
        sampleLst.append(param_dict)
    return sampleLst

def build_command(sample, journalFile, freeCadpath):
    freecad_exec_path = os.path.join(freeCadpath,  r"bin\FreeCADCmd.exe")
    cmd = [freecad_exec_path, journalFile, json.dumps(sample),] 
    return cmd

def calculate_objective(sample, freeCAD_journal, freeCADpath):
    res = None

    try:
        cmd = build_command(sample, freeCAD_journal, freeCADpath)

        print("\n==============================")
        print("PYTHON SAMPLE SENT:")
        print(sample)
        print("COMMAND:")
        print(cmd)

        res = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )

        print("FREECAD STDOUT LAST 20 LINES:")
        lines = res.stdout.splitlines()
        for line in lines[-20:]:
            print(repr(line))

        absorbed_energy = float(lines[-2])
        max_stress = float(lines[-1])

        print("PARSED VALUES:")
        print("absorbed_energy:", absorbed_energy)
        print("max_stress:", max_stress)

        return absorbed_energy, max_stress

    except Exception as e:
        print(f"Sample processing failed due to error: {e}")

        if res is not None:
            print("STDOUT:")
            print(res.stdout)
            print("STDERR:")
            print(res.stderr)

        time.sleep(1)
        return None, None

    
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
    # TODO: set the freecad path your the installation location of freeCAD
    freeCAD_path = r'C:/Program Files/FreeCAD 1.0' # default on windows


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


    # generates latin hypercube samples of the parameters
    nSamples = 3
    config = getConfig()
    # samples is a list of dictionary containing parameter:value pairs
    samples = generateSamples(config, nSamples)


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