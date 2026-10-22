import os

from time import perf_counter as timer
from .models.tsp import distance_matrix, successors
from .algorithms.baseline import DFS, BranchAndBound
from .models.state import State
from .utils.loader import load_location


def format_path(path):
    return " → ".join(
        "Deposito" if index == 0 else str(index)
        for index in path
    )


# Se la variabile d'ambiente non esiste, usa questo file.
file_path = os.getenv("file_path", "data/data.json")

locations = load_location(file_path)
matrix = distance_matrix(locations)

initial_state = State(
    path=(0,),
    unvisited=frozenset(range(1, len(locations))),
    cost=0.0,
)

print("STATO INIZIALE")
print(f"  Percorso: {format_path(initial_state.path)}")
print(f"  Consegne da effettuare: {len(initial_state.unvisited)}")
print(f"  Costo: {initial_state.cost:.3f}")

print("\nPRIME MOSSE POSSIBILI")

for state in successors(initial_state, matrix):
    remaining = ", ".join(str(i) for i in sorted(state.unvisited))
    print(
        f"  {format_path(state.path)}"
        f" | Costo: {state.cost:.3f}"
        f" | Da visitare: {remaining}"
    )

print("\nAvvio branch-and-bound...", flush=True)
start = timer()

best_bnb = BranchAndBound(initial_state, matrix)

bnb_time = timer() - start

print("\nMIGLIOR GIRO TROVATO CON BRANCH AND BOUND")
print(f"  {format_path(best_bnb.path)}")
print(f"  Costo totale: {best_bnb.cost:.3f}")
print(f"  Tempo: {bnb_time:.3f} secondi", flush=True)

print("\nAvvio DFS...", flush=True)
start = timer()

best_dfs = min(
    DFS(initial_state, matrix),
    key=lambda state: state.cost,
)

dfs_time = timer() - start

print("\nMIGLIOR GIRO TROVATO CON DFS")
print(f"  {format_path(best_dfs.path)}")
print(f"  Costo totale: {best_dfs.cost:.3f}")
print(f"  Tempo: {dfs_time:.3f} secondi")
