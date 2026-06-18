# Constrained FEM Surrogate Optimization with Gaussian Processes

This repository contains a constrained geometry optimization workflow for an engineering design problem. The goal is to optimize the placement of three cutouts in a 60 × 60 mm aluminum back plate to maximize absorbed deformation energy while respecting a maximum stress constraint.

The expensive objective evaluation is a FreeCAD/CalculiX FEM simulation. To reduce the number of required simulations, the workflow combines Design of Experiments (DoE), geometry constraint filtering, Gaussian Process surrogate models, and acquisition-based candidate selection.

## Problem

The design contains seven optimization variables:

* `x1`, `y1`: center position of circular cutout 1
* `x2`, `y2`: center position of circular cutout 2
* `x3`, `y3`: center position of the elongated cutout
* `angle`: rotation angle of the elongated cutout

The optimization target is:

* maximize absorbed plastic deformation energy
* keep maximum stress below 275 MPa
* satisfy all geometric constraints, especially edge clearance and minimum distance between cutouts

## Method

The implemented workflow is:

1. Generate candidate geometries using Latin Hypercube Sampling.
2. Filter invalid geometries before running FEM simulations.
3. Run valid candidates through the FreeCAD/CalculiX FEM model.
4. Store absorbed energy and maximum stress values in CSV files.
5. Train two Gaussian Process surrogate models:

   * one model for absorbed energy
   * one model for maximum stress
6. Score a large pool of new valid candidate geometries using an acquisition function.
7. Evaluate only the best surrogate-selected candidates with the expensive FEM model.
8. Append the new results to the dataset for further surrogate updates.

The acquisition score uses an Upper Confidence Bound (UCB) term for absorbed energy and a soft penalty for violating the stress constraint:

```text
score = (mu_energy + beta * sigma_energy) * penalty(stress)
```

This favors candidates with high predicted energy while still accounting for model uncertainty and the 275 MPa stress limit.

## Repository Structure

```text
.
├── main.py                    # Initial DoE sampling, geometry filtering, FEM runs, result logging
├── gp_predict.py              # GP training, surrogate-based candidate scoring, FEM validation
├── full_journal_fc.py         # FreeCAD journal script for geometry update and FEM execution
├── csvtoexcel.py              # Converts result CSV files to formatted Excel files
├── config.json                # Parameter bounds for the seven design variables
├── optml_master.FCStd         # Parameterized FreeCAD model
├── all_results.csv            # Full simulation dataset, created/extended during runs
├── results.csv                # Best result per run, created/extended during runs
├── all_results_clean.xlsx     # Optional formatted Excel export
├── results_clean.xlsx         # Optional formatted Excel export
└── mlopt_engineering_project_V2.pdf
```

## Requirements

Python 3.12 was used for this project.

Required Python packages:

```text
numpy
scipy
pandas
matplotlib
scikit-learn
openpyxl
```

Install them with:

```bash
pip install -r requirements.txt
```

External dependency:

* FreeCAD 1.0.x with CalculiX/FEM support
* On Windows, the default executable path used in the scripts is:

```text
C:/Program Files/FreeCAD 1.0/bin/FreeCADCmd.exe
```

If FreeCAD is installed elsewhere, update `freeCADExecPath` in `main.py` and `gp_predict.py`.

## Usage

### 1. Configure parameter bounds

Edit `config.json`:

```json
{
  "dsParameterBounds": {
    "x1": [11, 49],
    "y1": [11, 19],
    "x2": [8, 52],
    "y2": [8, 52],
    "x3": [9.5, 50.5],
    "y3": [9.5, 50.5],
    "angle": [0, 180]
  }
}
```

The parameter names must match the spreadsheet entries in `optml_master.FCStd`.

### 2. Generate initial FEM data

Run:

```bash
python main.py
```

This generates Latin Hypercube samples, filters invalid geometries, runs the FEM simulation for valid samples, and appends the results to:

* `all_results.csv`
* `results.csv`

### 3. Run surrogate-based optimization

After `all_results.csv` contains initial FEM data, run:

```bash
python gp_predict.py
```

This trains Gaussian Process models on the existing data, samples a large candidate pool, ranks valid candidates by surrogate score, runs FEM simulations for the best candidates, and appends the new results to the CSV files.

### 4. Convert results to Excel

Run:

```bash
python csvtoexcel.py
```

This creates formatted Excel files from the CSV result files.

## Output Files

* `all_results.csv`: all evaluated FEM samples
* `results.csv`: best evaluated sample per optimization run
* `all_results_clean.xlsx`: formatted full dataset
* `results_clean.xlsx`: formatted best-results dataset

Each result row contains the seven design variables plus:

```text
energy_objective, stress_constraint, date
```

## Notes

* `gp_predict.py` requires an existing `all_results.csv` file.
* Invalid geometries are filtered before starting FreeCAD to avoid unnecessary FEM runs.
* The FreeCAD script updates the spreadsheet parameters, recomputes the model, runs CalculiX, and extracts absorbed energy and maximum stress from the FEM result.
* The FreeCAD model and FEM base setup were provided as part of the course project; the optimization workflow, constraint handling, surrogate modeling, and result-processing code were developed for this solution.

## Course Context

Project for the course "Optimization and Machine Learning" at ETH Zurich.
