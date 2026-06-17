# ML Optimization Engineering Project

## Overview

This project implements a **Design of Experiments (DoE) and Gaussian Process-based optimization** framework to solve costly engineering design problems. The goal is to find optimal part design parameters under constraints while minimizing expensive FEM (Finite Element Method) simulations.

## Problem Statement

Finding optimal designs through brute-force FEM simulation is computationally expensive. This project applies machine learning techniques to:
- Use Design of Experiments to intelligently select sample designs
- Train Gaussian Process regressors as surrogate models for FEM results
- Optimize design parameters efficiently without running every possible configuration

## Project Structure

### Core Scripts

- **main.py** — Main optimization engine. Orchestrates the DoE sampling strategy, FEM simulations, GP model training, and parameter optimization.
- **gp_predict.py** — Advanced Gaussian Process models for predicting absorbed energy and maximum stress. Includes expected improvement (EI) acquisition functions.
- **full_journal_fc.py** — FreeCAD journal script that interfaces with the CAD model (optml_master.FCStd). Runs FEM simulations for parameter evaluation.
- **csvtoexcel.py** — Utility to convert CSV results to Excel format for reporting.
- **visualize_sample_gui.py** — GUI visualization tool for sampling strategy and results.

### Configuration & Data

- **config.json** — Parameter bounds for design variables (x1, y1, x2, y2, x3, y3, angle).
- **debug_config.json** — Alternative configuration for debugging.
- **optml_master.FCStd** — FreeCAD part file with parameterized design. Contains the Spreadsheet object for parameter updates.
- **all_results.csv / all_results_clean.xlsx** — Complete simulation results dataset.
- **results.csv / results_clean.xlsx** — Filtered/processed results.

## Requirements

### Python Packages

Install with:
```bash
pip install -r requirements.txt
```

### External Dependencies

- **FreeCAD** (manual installation required) — Used for CAD modeling and FEM simulations.
  - Must be installed and accessible from the command line
  - The project runs FreeCAD as a subprocess to execute journal scripts
  - Visit [FreeCAD Official Site](https://www.freecadweb.org/) for installation

- **Python 3.12+**

## Usage

### 1. Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure FreeCAD is installed and accessible.

3. Update configuration parameters in `config.json` to match your design variables and bounds:
   ```json
   {
       "dsParameterBounds": {
           "param_name": [lower_bound, upper_bound],
           ...
       }
   }
   ```

### 2. Run Optimization

Execute the main optimization loop:
```bash
python main.py
```

This will:
- Load design parameter bounds from config.json
- Generate initial DoE samples (Latin Hypercube Sampling)
- Run FEM simulations via FreeCAD for each sample
- Collect absorbed energy and maximum stress results
- Train Gaussian Process regressors on results
- Iteratively select new samples using expected improvement
- Output results to CSV/Excel files

### 3. Visualization & Analysis

View sampling strategy and results:
```bash
python visualize_sample_gui.py
```

Convert results to Excel format:
```bash
python csvtoexcel.py
```

## Technical Approach

### Design of Experiments (DoE)
- **Latin Hypercube Sampling (LHS)** — Initial design generation for uniform coverage of design space
- **Expected Improvement (EI)** — Acquisition function for sequential sampling

### Gaussian Process Models
- Separate models for absorbed energy and maximum stress
- RBF (Radial Basis Function) kernels with optimized hyperparameters
- Kernel composition: `ConstantKernel * RBF + WhiteKernel` for robust predictions
- Separate length scales per design variable

### Constraints
- Design variables must satisfy bounds defined in config.json
- Edge distance constraints can be configured via parameter bounds

## Output Files

- **all_results.csv** — Complete simulation dataset with all samples
- **all_results_clean.xlsx** — Cleaned and formatted results in Excel
- **results.csv / results_clean.xlsx** — Subset of results for reporting
- **Optimization Project Changelog.txt** — Project version history and notes

## Project Evolution

- **V1** — Initial implementation with basic coordinate constraints
- **V2** — Improved coordinate system and constraint handling; separation of absorbed energy and stress models

See `mlopt_engineering_project_V2.pdf` for detailed project specification and theoretical background.

## Notes

- Ensure parameter names in config.json match the Spreadsheet object variables in optml_master.FCStd
- Constraint satisfaction is validated before running costly FEM simulations
- Results are cached to avoid duplicate simulations
- Edge distance constraints are handled through parameter bounds configuration

## License & Attribution

This project was created as an educational exercise in Design of Experiments and machine learning-based optimization.
