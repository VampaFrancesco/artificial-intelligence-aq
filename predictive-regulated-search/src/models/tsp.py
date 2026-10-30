from math import sqrt
from .node import Node
from .state import State

def distance(i: Node, j: Node):
    x1, y1 = i.x, i.y
    x2, y2 = j.x, j.y
    d = sqrt((x2-x1)**2 + (y2-y1)**2)
    return d

def distance_matrix(locations):
    matrix = [[0 for _ in range(len(locations))] for _ in range(len(locations))]
    for i in range(len(locations)):
        for j in range(len(locations)):
            matrix[i][j] = distance(locations[i], locations[j])
    return matrix

def successors(state, matrix):
    next_states = []

    for node in sorted(state.unvisited):
        next_state = State(
            path=state.path + (node,),
            unvisited=state.unvisited - {node},
            cost=state.cost+matrix[state.current_node][node]
        )
        next_states.append(next_state)
    return next_states
    
