from dataclasses import dataclass
from .node import Node

@dataclass
class State:
    unvisited: frozenset[int]
    path: tuple[int, ...]
    cost: float
    
    @property
    def current_node(self) -> int:
        return self.path[-1]