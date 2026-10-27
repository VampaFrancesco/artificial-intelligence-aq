from .predictor import extract_features, predict_remaining_cost
from ..models.state import State
from ..models.tsp import successors
from .regulator import should_diversify

def estimated_total_cost(state, matrix, model_data):
    if len(state.unvisited) == 0:
        return state.cost + matrix[state.current_node][0]
    else:
        remaining_cost = predict_remaining_cost(extract_features(state, matrix),model_data)

    return state.cost + remaining_cost


def predictiveSearch(initial_state, matrix, max_states, model_data, patience=None):
    """Restituisce il miglior giro, il completamento della ricerca e le statistiche."""
    stack = [initial_state]
    best_cost = float("inf")
    best_state = None
    states_examined = 0
    states_pruned = 0
    states_pruned_before_push = 0
    completed_tours = 0
    states_since_improvements = 0
    diversification_steps = 0
    states_since_diversification = 0
    


    while stack and states_examined < max_states:
        if (
            patience is not None
            and should_diversify(states_since_improvements, patience)
            and states_since_diversification >= patience
        ):
            lowest_cost_index = 0
            for index in range(len(stack)):
                if stack[index].cost < stack[lowest_cost_index].cost:
                    lowest_cost_index = index

            state = stack.pop(lowest_cost_index)
            diversification_steps+=1
            states_since_diversification = 0
        else:
            state = stack.pop()
            states_since_diversification += 1
        
        states_examined += 1
        states_since_improvements += 1

        if state.cost >= best_cost:
            states_pruned += 1
            continue

        if not state.unvisited:
            completed_tours += 1
            total_cost = state.cost + matrix[state.current_node][0]

            if total_cost < best_cost:
                best_cost = total_cost
                states_since_improvements = 0
                best_state = State(
                    path=state.path + (0,),
                    unvisited=state.unvisited,
                    cost=total_cost,
                )
        else:
            next_states = successors(state,matrix)
            next_states.sort(
                key=lambda candidate: estimated_total_cost(candidate, matrix, model_data),
                reverse=True
            )
            for next in next_states:
                if next.cost < best_cost:
                    stack.append(next)
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
        "diversification_steps": diversification_steps
    }
    return best_state, not stack, stats

        