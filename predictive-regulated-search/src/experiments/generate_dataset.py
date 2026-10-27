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


def path_cost(path, matrix):
    return sum(matrix[a][b] for a, b in zip(path, path[1:]))


def nearest_completion(state, matrix, first=None):
    """Completa il percorso scegliendo ogni volta la consegna più vicina."""
    remaining = set(state.unvisited)
    route = [state.current_node]
    if first is not None:
        if first not in remaining:
            raise ValueError("La prima consegna deve essere ancora da visitare.")
        route.append(first)
        remaining.remove(first)
    while remaining:
        next_node = min(remaining, key=lambda node: (matrix[route[-1]][node], node))
        route.append(next_node)
        remaining.remove(next_node)
    route.append(0)
    return route


def improve_route(route, matrix, passes=6):
    """2-opt: inverte tratti del giro quando la distanza diminuisce.

    Il primo e l'ultimo nodo restano fissi. Si migliora solo il completamento,
    quindi il percorso parziale da cui si parte non viene modificato.
    """
    route = list(route)
    for _ in range(passes):
        improved = False
        for left in range(1, len(route) - 2):
            for right in range(left + 1, len(route) - 1):
                a, b = route[left - 1], route[left]
                c, d = route[right], route[right + 1]
                change = matrix[a][c] + matrix[b][d] - matrix[a][b] - matrix[c][d]
                if change < -1e-10:
                    route[left:right + 1] = reversed(route[left:right + 1])
                    improved = True
        if not improved:
            break
    return route


def reference_completion(state, matrix, starts=3, passes=6):
    """Restituisce un buon giro ammissibile; non dimostra che sia il migliore."""
    if not state.unvisited:
        return State(path=state.path + (0,), unvisited=frozenset(),
                     cost=state.cost + matrix[state.current_node][0])
    first_choices = sorted(state.unvisited,
                           key=lambda node: (matrix[state.current_node][node], node))[:starts]
    best = None
    for first in first_choices:
        route = improve_route(nearest_completion(state, matrix, first), matrix, passes)
        candidate = State(path=state.path + tuple(route[1:]), unvisited=frozenset(),
                          cost=state.cost + path_cost(route, matrix))
        if best is None or candidate.cost < best.cost:
            best = candidate
    return best


def collect_approximate_examples(locations, instance_id, random_seed, count=40):
    """Campiona stati e target ammissibili per mappe grandi, senza ricerca esaustiva."""
    matrix = distance_matrix(locations)
    n_deliveries = len(locations) - 1
    if n_deliveries < 1 or count < 2:
        raise ValueError("Servono almeno una consegna e due esempi.")
    initial = State(path=(0,), unvisited=frozenset(range(1, len(matrix))), cost=0.0)
    random_order = list(range(1, len(matrix)))
    Random(random_seed).shuffle(random_order)
    nearby_order = nearest_completion(initial, matrix)[1:-1]
    examples = []
    for index in range(count):
        depth = round(index * (n_deliveries - 1) / (count - 1))
        order = random_order if index % 2 else nearby_order
        prefix = (0,) + tuple(order[:depth])
        state = State(path=prefix, unvisited=initial.unvisited - set(prefix),
                      cost=path_cost(prefix, matrix))
        completion = reference_completion(state, matrix)
        examples.append({
            "instance_id": instance_id,
            "state": {"path": list(state.path), "unvisited": sorted(state.unvisited),
                      "cost": state.cost},
            "target_cost_to_go": completion.cost - state.cost,
            "target_is_certified": False,
            "reference_path": list(completion.path),
        })
    return examples


def generate_large_dataset(n_deliveries=100, training_maps=12, test_maps=3,
                           examples_per_map=40, progress=None):
    """Un solo dataset persistente: coordinate, esempi e separazione train/test."""
    if n_deliveries < 1 or not 1 <= training_maps <= 10000 or test_maps < 1:
        raise ValueError("Dimensioni del dataset non valide.")
    dataset = {
        "metadata": {
            "deliveries_per_map": n_deliveries,
            "target_method": "nearest_neighbor_3_starts_2opt_6_passes",
            "targets_are_certified": False,
            "examples_per_map": examples_per_map,
            "training_seeds": [10000 + i for i in range(training_maps)],
            "test_seeds": [20000 + i for i in range(test_maps)],
        },
        "splits": {"train": [], "test": []},
        "instances": {}, "examples": [],
    }
    for split, label, count, first_seed in (
        ("train", "allenamento", training_maps, 10000),
        ("test", "prova", test_maps, 20000),
    ):
        for number in range(count):
            seed = first_seed + number
            name = f"{label}_{number + 1:02d}"
            locations = generate_locations(n_deliveries, seed)
            dataset["instances"][name] = [{"x": node.x, "y": node.y} for node in locations]
            dataset["splits"][split].append(name)
            dataset["examples"].extend(collect_approximate_examples(
                locations, name, random_seed=seed + 30000, count=examples_per_map,
            ))
            if progress is not None:
                progress(f"Mappa di {label} {number + 1}/{count}: {n_deliveries} consegne")
    return dataset
