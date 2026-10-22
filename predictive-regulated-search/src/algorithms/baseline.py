from src.models.state import State
from src.models.tsp import locations, distance_matrix, successors


def DFS(initial_state, matrix):
    stack = [initial_state]

    while stack:
        state = stack.pop()

        if not state.unvisited:
            yield State(
                path= state.path + (0,),
                unvisited=state.unvisited,
                cost=state.cost + matrix[state.current_node][0],
            )
        else:
            stack.extend(successors(state, matrix))


def BranchAndBound(initial_state, matrix):
    stack = [initial_state]
    best_cost = float("inf")
    best_state = None

    while stack:
        state = stack.pop()

        if state.cost >= best_cost:
            continue

        if not state.unvisited:
            total_cost = state.cost + matrix[state.current_node][0]

            if total_cost < best_cost:
                best_cost = total_cost
                best_state = State(
                    path=state.path + (0,),
                    unvisited=state.unvisited,
                    cost=total_cost,
                )
        else:
            for next_state in successors(state, matrix):
                if next_state.cost < best_cost:
                    stack.append(next_state)

    return best_state