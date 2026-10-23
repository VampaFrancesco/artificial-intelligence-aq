from ..models.tsp import distance_matrix, successors
from ..models.state import State
from ..algorithms.baseline import BranchAndBound
from random import Random
from ..models.node import Node


def generate_locations(n_deliveries, seed):
    # Con lo stesso seed otteniamo le stesse coordinate, utili per ripetere l'esperimento.
    rng = Random(seed)
    locations = [Node(0, 0)]

    for _ in range(n_deliveries):
        node = Node(
            x=rng.uniform(0, 100),
            y=rng.uniform(0, 100),
        )
        locations.append(node)

    return locations


def collect_examples(locations, instance_id, max_states, max_depth = 6):
    # Raccoglie stati parziali e il costo rimanente ottimo certificato dal B&B.
    dataset = []
    matrix = distance_matrix(locations)

    initial_state = State(
        path=(0,),
        unvisited=frozenset(range(1, len(locations))),
        cost=0.0,
    )

    # Partiamo dagli stati dopo una consegna; la pila serve a visitarne anche i figli.
    stack = list(successors(initial_state, matrix))

    while stack:
        partial_state = stack.pop()
        # Il deposito iniziale non conta come consegna effettuata.
        depth = len(partial_state.path) - 1

        # max_depth limita gli stati raccolti, non il completamento cercato dal B&B.
        if depth < max_depth:
            stack.extend(successors(partial_state, matrix))
        best_completion, is_complete, stats = BranchAndBound(
            partial_state,
            matrix,
            max_states=max_states,
        )

        # Conserviamo solo target certificati: una ricerca interrotta non basta.
        if is_complete and best_completion is not None:
            # Il giro completo include il costo già percorso: sottraiamolo.
            target = best_completion.cost - partial_state.cost

            example = {
                "instance_id": instance_id,
                "state": {
                    "path": list(partial_state.path),
                    "unvisited": sorted(partial_state.unvisited),
                    "cost": partial_state.cost,
                },
                "target_cost_to_go": target,
            }

            dataset.append(example)

    return dataset
