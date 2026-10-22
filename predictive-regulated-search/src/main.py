from .models.state import State
from .models.tsp import locations

initial_state = State(
    path=(0,),
    unvisited=frozenset(range(1, len(locations))),
    cost=0.0,
)
