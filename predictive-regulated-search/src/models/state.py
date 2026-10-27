from dataclasses import dataclass
@dataclass(frozen=True)
class State:
    unvisited: frozenset[int]
    path: tuple[int, ...]
    cost: float

    @property
    def current_node(self) -> int:
        return self.path[-1]


