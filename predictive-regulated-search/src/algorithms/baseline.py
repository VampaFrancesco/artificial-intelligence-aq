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


def BranchAndBound(initial_state, matrix, max_states):
    """Restituisce il miglior giro, il completamento della ricerca e le statistiche."""
    stack = [initial_state]
    best_cost = float("inf")
    best_state = None
    states_examined = 0
    states_pruned = 0
    states_pruned_before_push = 0
    completed_tours = 0

    while stack and states_examined < max_states:
        state = stack.pop()
        states_examined += 1

        if state.cost >= best_cost:
            states_pruned += 1
            continue

        if not state.unvisited:
            completed_tours += 1
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
                else:
                    states_pruned_before_push += 1
    active_frontier_size = 0

    for pending_state in stack:
        if pending_state.cost < best_cost:
            active_frontier_size += 1

    horizon_size = (
        completed_tours
        + states_pruned
        + states_pruned_before_push
        + len(stack)
    )
    stats = {
        "states_examined": states_examined,
        "states_pruned": states_pruned,
        "states_pruned_before_push": states_pruned_before_push,
        "pending_states": len(stack),
        "active_frontier_size": active_frontier_size,
        "completed_tours": completed_tours,
        "horizon_size": horizon_size,
    }
    return best_state, not stack, stats
