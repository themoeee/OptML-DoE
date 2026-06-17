import os
import math
import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel, Matern
from datetime import datetime
from pathlib import Path
from scipy.stats import norm
import scipy.stats.qmc as qmc
import json
from main import get_valid_samples, calculate_objective
import heapq
import itertools

def train_absorbed_energy_gp(x_train, y_train_ae):
    """This function trains a GP model for the absorbed energy for later Bayesian optimization"""

    print(f"Training GP for absorbed energy on {len(x_train)} samples")
   
    kernel = (
        ConstantKernel(1.0, (1e-2, 1e3))
        * RBF(
            length_scale=np.ones(x_train.shape[1]),   # can learn different lenght scales for different variables, makes sense as angle is different to coordinates
            length_scale_bounds=(1e-2, 1e2),
        )
        + WhiteKernel(noise_level=1e-6, noise_level_bounds=(1e-9, 1e-2))
    )

    gp_absorbed_energy = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=15, normalize_y=True)
    gp_absorbed_energy.fit(x_train, y_train_ae)
    print("Training done\n GP absorbed energy: ", gp_absorbed_energy.kernel_)   #shows the kernel after hyperparam optimization
    return gp_absorbed_energy

def train_max_stress_gp(x_train, y_train_ms):
    """This function trains a GP model for the maximum stress for later Bayesian optimization"""

    print(f"Training GP for maximum stress on {len(y_train_ms)} samples")

    kernel = (
        ConstantKernel(1.0, (1e-2, 1e3))
        * Matern(
            length_scale=np.ones(x_train.shape[1]) * 10.0,
            length_scale_bounds=(1e-1, 1e2),
            nu=1.5
        )
        + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-8, 1e-1))
    )

    gp_max_stress = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=15, normalize_y=True)
    gp_max_stress.fit(x_train, y_train_ms)
    print("Training done\n GP max stress: ", gp_max_stress.kernel_)
    return gp_max_stress

def predict(gp_energy, gp_stress, x_test):
    """This function predicts the absorbed energy and maximum stress as well as their uncertainties for a given test point using the learned GPs"""
    #print("Predicting with GPs")
    y_pred_energy, sigma_energy = gp_energy.predict(x_test, return_std=True)
    y_pred_stress, sigma_stress = gp_stress.predict(x_test, return_std=True)
    return y_pred_energy, sigma_energy, y_pred_stress, sigma_stress

def calculate_score(gp_energy, gp_stress, x):
    """This function calculates a new score using a combination of the stress and absorbed energy surrogate models for Bayesian Optimization"""

    MAX_STRESS = 275

    try:
        energy, sigma_energy, stress, sigma_stress = predict(gp_energy, gp_stress, x)
    except Exception as e:
        print("Error during prediction: ", e)
        return None
    
    # score should look like this: 
    # lets use UCB (upper confidence bound) as acquisition function
    beta = 1  # Exploration-exploitation trade-off parameter, can be tuned - I chose 1 here most of times, now I'll try to exploite more
    score_UCB = (energy + beta * sigma_energy)
    
    # Here I want to add a penalty factor for the stress constraint
    beta2 = 0.0     # This here is used to be a bit more conservative when it comes to the stress constraint. Before, we would often sample points with low stresses (as they get a high score), but they were often too optimistic and underestimated the atual stress. This now will lead to having a higher penalty on points where the GP is unsure
    stress_thr = stress + beta2 * sigma_stress   # I started with beta = 2, but I think this is too conservative   

    z = (stress - MAX_STRESS) / sigma_stress
    penalty = np.exp(-0.5 * np.maximum(z, 0)**2)

   # p_safe = norm.cdf((MAX_STRESS - stress_thr) / sigma_stress)  

    score = score_UCB * penalty #p_safe

    # asarray, squeeze and float used here to get rid of useless array formating
    return float(np.asarray(score).squeeze()), float(np.asarray(energy).squeeze()), float(np.asarray(stress).squeeze())

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

    print("Finished generating samples")
    return sampleLst

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

def save_data_to_csv(best_gp_candidates):
    csv_path = Path("results.csv")
    csv_path_all_results = Path("all_results.csv")

    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []

    for candidate in best_gp_candidates:
        row = candidate["sample"].copy()
        row["energy_objective"] = candidate["actual_absorbed_energy"]
        row["stress_constraint"] = candidate["actual_stress"]
        row["date"] = date
        results.append(row)

    columns = [
        "x1", "y1", "x2", "y2", "x3", "y3", "angle",
        "energy_objective", "stress_constraint", "date"
    ]

    pd.DataFrame(results)[columns].to_csv(
        csv_path_all_results,
        mode="a",
        header=not csv_path_all_results.exists(),
        index=False
    )

    best_result = max(
        results,
        key=lambda row: row["energy_objective"]
    )

    pd.DataFrame([best_result])[columns].to_csv(
        csv_path,
        mode="a",
        header=not csv_path.exists(),
        index=False
    )

def main():
    'GEOMETRY DEFINITION'
    r1 = 9
    r2 = 6
    a = 25/2
    b = 7.5 #radius

    freeCADExecPath = r'C:/Program Files/FreeCAD 1.0/bin/FreeCADCmd.exe'
    freeCAD_journal = os.path.join(os.getcwd(), "full_journal_fc.py")

    csv_path = os.path.join(os.getcwd(), "all_results.csv")

    df = pd.read_csv(csv_path)
    
    # Extract parameters x1-x7 as input features
    x_train = df[['x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'angle']].values
    
    # Extract outputs
    y_train_ae = df['energy_objective'].values  # absorbed energies
    y_train_ms = df['stress_constraint'].values  # stresses
    print("Successfully loaded training data from CSV file")
    
    # print(x_train.shape, y_train_ae.shape, y_train_ms.shape)
    # idx = 4
    # print(x_train[idx], y_train_ae[idx], y_train_ms[idx])

    # Train GPs
    gp_ae = train_absorbed_energy_gp(x_train, y_train_ae)
    gp_ms = train_max_stress_gp(x_train, y_train_ms)

    #Get config and specify number of points to sample from
    config = getConfig()

    nSamples = 10000000
   
    # samples is a list of dictionary containing parameter:value pairs
    samples = generateSamples(config, nSamples)  

    valid_samples = get_valid_samples(samples, r1, r2, a, b)
    
    samples = valid_samples
    print(f"After checking for validity, there are {len(samples)} left")

            # #Predicting for a new test point:
            # x_test = np.array([[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 45]])  # Example test point, not feasible though
            # y_pred_ae, sigma_ae, y_pred_ms, sigma_ms = predict(gp_ae, gp_ms, x_test)
            # print(f"Predicted absorbed energy: {y_pred_ae[0]:.2f} ± {sigma_ae[0]:.2f}")
            # print(f"Predicted max stress: {y_pred_ms[0]:.2f} ± {sigma_ms[0]:.2f}")  

    # Okay, so now we got a surrogate model for the absorbed energy (objective) and the max stress (constraint)
    # The idea is now to use both of these models in combination to sample new interesting points and do bayesian optimization (zero'th order)
    # I will therefore calculate a new "score" as a objective goal, which uses Lagrangian penalty method to combine these two models and also account for uncertainty

    n_test_points = 5
    best_gp_candidates = [{"sample": None, "score": float('-inf')} for _ in range(n_test_points)]
    top_k = []
    counter = itertools.count()  #used as tiebreaker in case of identical score values

    #ChatGPT recommended using heapq to be computationally efficient
    PARAM_NAMES = ['x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'angle']

    for sample in valid_samples:
        x = np.array([[sample[p] for p in PARAM_NAMES]])

        score, energy, stress = calculate_score(gp_ae, gp_ms, x) # np.array([list(sample.values())])

        item = (score, next(counter), sample, energy, stress)

        if len(top_k) < n_test_points:
            heapq.heappush(top_k, item)

        elif score > top_k[0][0]:
            heapq.heapreplace(top_k, item)

    best_gp_candidates = [
    {
        "score": score,
        "sample": sample,
        "predicted_energy": energy,
        "predicted_stress": stress, 
        "actual_absorbed_energy": None,
        "actual_stress": None,
    }
    for score, _, sample, energy, stress in sorted(top_k, key=lambda item: item[0], reverse=True)
    ]

    print("\nBest GP candidates:")
    for candidate in best_gp_candidates:
        print(f"score = {candidate['score']:.6g}, sample = {candidate['sample']}, predicted energy = {candidate['predicted_energy']:.2f}, predicted stress = {candidate['predicted_stress']:.2f}")

    for candidate in best_gp_candidates:
        # Here I want to compare the results of the GPs with the actual simulation to validate the predictions
        absorbed_energy, max_stress = calculate_objective(candidate['sample'], freeCAD_journal, freeCADExecPath)
        if absorbed_energy is not None:
            print(f"Sample {candidate['sample']} -> Absorbed Energy: {absorbed_energy}, Max Stress: {max_stress}")
            candidate['actual_absorbed_energy'] = absorbed_energy
            candidate['actual_stress'] = max_stress

        # ToDo: Save new values into both csv files, to further expand the training dataset and save computations   

    for sample in best_gp_candidates:
        print(f"Predicted Energy: {sample['predicted_energy']:.2f}, Actual Energy: {sample['actual_absorbed_energy']}, Predicted Stress: {sample['predicted_stress']:.2f}, Actual Stress: {sample['actual_stress']}")
        stress_error = abs(sample['predicted_stress'] - sample['actual_stress']) / sample['actual_stress'] * 100 
        energy_error = abs(sample['predicted_energy'] - sample['actual_absorbed_energy']) / sample['actual_absorbed_energy'] * 100
        print(f"Energy prediction error: {energy_error:.2f}%, Stress prediction error: {stress_error:.2f}%\n")

    save_data_to_csv(best_gp_candidates)

if __name__ == "__main__":
    main()