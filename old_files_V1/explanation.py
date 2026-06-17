"""
Okay, so this should help as a quick reference

We have 7 design variables, 6 are the positions of the circles and the oval cutout, 1 is the angle

The constraints are the following:

GEOMETRIC:
Distance to edges >2mm        --- easy, just check
Distance between cutouts >1mm --- more complicated, relative

STRESS:
Max stress 275 MPa

Optimization goal
MAXIMIZE DEFORMATION ENERGY

OVERALL GEOMETRY:
REAR END HAS MIDDLE POINT AT (0,0), EDGES IN RANGE (-30, 30)
MEANING OVERALL SIZE OF SQUARE IS 60x60

FORMAT: 
sample: {param1: value1, param2: value2, ...} up until 
output: {param1: value1, param2: value2, ..., energy_objective: value, stress_constraint: value}
#{'x1': 10.626521363596474, 'y1': 10.061085186068292, 'x2': 10.40954922455789, 'y2': 10.83505130299418, 'x3': 1.0716821452429097, 'y3': 10.395763887674155, 'angle': 11.093705475638817, 'energy_objective': 12987.858503573148, 'stress_constraint': 246.33625}, {'x1': 10.24003987027264, 'y1': 10.479518423992992, 'x2': 10.851821807442654, 'y2': 10.660059413214857, 'x3': 1.9842858173887628, 'y3': 10.066683460705365, 'angle': 13.250739468771107, 'energy_objective': 12920.678049560782, 'stress_constraint': 238.6405}



DOCUMENTATION:
So I started and spent >1h trying to fix the error, turns out it was FreeCAD 1.1, had to switch to 1.0.2



"""