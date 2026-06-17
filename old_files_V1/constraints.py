import math
import numpy as np

#how do i get access to the variable value x1 in a json dictionary? 


def calculate_edge_dist(config):

    r1 = 6
    r2 = 9
    a = 25/2
    b = 7.5

    params = config['dsParameterBounds']

    #Cirlce 1
    x1 = params['x1']
    y1 = params['y1']
    d_circle1 = 30 - ( max( abs(x1), abs(y1)) + r1)
    print("Distance Circle 1 to edge: ", d_circle1)

    #Circle 2
    x2 = params['x2']
    y2 = params['y2']
    d_circle2 = 30 - ( max( abs(x2), abs(y2)) + r2)
    print("Distance Circle 2 to edge: ", d_circle2)


    #Oval shape
    x3 = params['x3']
    y3 = params['y3']
    angle = params['angle']

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

    print("Distance Oval to Circle 1 (focal point 1): ", d_oval_c1_11)
    print("Distance Oval to Circle 1 (focal point 2): ", d_oval_c1_12)
    print("Distance Oval to Circle 1 (perpendicular): ", d_oval_c1_2)
    print("Distance Oval to Circle 1 (perpendicular test): ", d_oval_c1_2test)

    #distance to circle 2
    d_oval_c2_1 = math.sqrt((x1-x2)**2+(y1-y2)**2) - r1 - b
    d_oval_c2_2 = abs( (x3-xh)*math.sin(angle) - (y3-yh)*math.cos(angle))

    pass
