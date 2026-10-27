from math import sqrt
from .node import Node
from.state import State

depot = Node(0, 0)
delivery1 = Node(3, 4)
delivery2 = Node(6, 1)
delivery3 = Node(8, 7)
delivery4 = Node(2, 9)
delivery5 = Node(5, 6)
delivery6 = Node(9, 3)

locations = [
    depot,
    delivery1,
    delivery2,
    delivery3,
    delivery4,
    delivery5,
    delivery6,
]

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
    
