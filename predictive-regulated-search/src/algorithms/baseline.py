from ..models.state import State
from ..models.tsp import successors
from math import isfinite
from time import perf_counter

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


def BranchAndBound(initial_state, matrix, max_states, observer=None, max_seconds=None):
    """Restituisce il miglior giro, il completamento della ricerca e le statistiche."""
    if max_states is not None and (
        not isinstance(max_states, int) or isinstance(max_states, bool) or max_states < 0
    ):
        raise ValueError("Il budget deve essere un intero non negativo.")
    if max_seconds is not None and (not isfinite(max_seconds) or max_seconds <= 0):
        raise ValueError("Il limite di tempo deve essere finito e positivo.")
    if max_states is None and max_seconds is None:
        raise ValueError("Serve un limite di stati o di tempo.")
    started = perf_counter()
    deadline = started + max_seconds if max_seconds is not None else None
    stack = [initial_state]
    best_cost = float("inf")
    best_state = None
    states_examined = 0
    states_pruned = 0
    states_pruned_before_push = 0
    completed_tours = 0
    states_expanded = 0

    while stack and (max_states is None or states_examined < max_states):
        if deadline is not None and perf_counter() >= deadline:
            break
        state = stack.pop()
        states_examined += 1
        if observer is not None:
            observer.selected(state, states_examined)

        if state.cost >= best_cost:
            states_pruned += 1
            continue

        if not state.unvisited:
            completed_tours += 1
            total_cost = state.cost + matrix[state.current_node][0]
            tour = State(path=state.path + (0,), unvisited=state.unvisited, cost=total_cost)
            if observer is not None:
                observer.tour(tour, states_examined, total_cost < best_cost)

            if total_cost < best_cost:
                best_cost = total_cost
                best_state = State(
                    path=state.path + (0,),
                    unvisited=state.unvisited,
                    cost=total_cost,
                )
        else:
            states_expanded += 1
            for next_state in successors(state, matrix):
                if next_state.cost < best_cost:
                    stack.append(next_state)
                else:
                    states_pruned_before_push += 1
    search_elapsed = perf_counter() - started
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
        "search_elapsed_seconds": search_elapsed,
        "stop_reason": ("frontier_exhausted" if not stack else
                        "time_limit" if deadline is not None and search_elapsed >= max_seconds
                        else "state_limit"),
        "states_expanded": states_expanded,
        "model_evaluations": 0,
        "diversification_candidates_scanned": 0,
        "states_pruned": states_pruned,
        "states_pruned_before_push": states_pruned_before_push,
        "pending_states": len(stack),
        "active_frontier_size": active_frontier_size,
        "completed_tours": completed_tours,
        "horizon_size": horizon_size,
    }
    if observer is not None:
        stats["root_choice"] = observer.summarize(stack, best_cost)
    return best_state, not stack, stats
