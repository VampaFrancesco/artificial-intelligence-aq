"""Preferenze sulle prossime consegne e monitoraggio dei relativi sottoalberi.

Le probabilità restano fisse durante una ricerca: non sono confidenze calibrate
né probabilità che una consegna sia ottima. Il monitor non sceglie stati.
"""

from math import exp, isfinite

from .predictor import extract_features, predict_remaining_cost
from ..models.tsp import successors


def estimated_total_cost(state, matrix, model_data):
    if not state.unvisited:
        return state.cost + matrix[state.current_node][0]
    return state.cost + predict_remaining_cost(extract_features(state, matrix), model_data)


def action_distribution(initial_state, matrix, model_data, temperature=None):
    """Softmax dei costi totali stimati dei successori dello stato iniziale.

    La temperatura predefinita è la distanza media tra coppie di luoghi.
    Il valore 1 è usato solo per l'istanza degenere con tutte le distanze nulle.
    """
    if temperature is None:
        distances = [matrix[i][j] for i in range(len(matrix)) for j in range(i)]
        temperature = sum(distances) / len(distances) if distances else 1.0
        temperature = temperature or 1.0
    if not isfinite(temperature) or temperature <= 0:
        raise ValueError("La temperatura deve essere finita e positiva.")

    candidates = successors(initial_state, matrix)
    scores = [estimated_total_cost(state, matrix, model_data) for state in candidates]
    if any(not isfinite(score) for score in scores):
        raise ValueError("Le stime dei costi devono essere finite.")
    if not candidates:
        return {"temperature": temperature, "alternatives": []}

    minimum = min(scores)
    weights = [exp(-(score - minimum) / temperature) for score in scores]
    normalizer = sum(weights)
    order = sorted(range(len(scores)), key=lambda index: (scores[index], index))
    ranks = {index: rank for rank, index in enumerate(order, 1)}
    return {
        "temperature": temperature,
        "alternatives": [
            {
                "action": state.current_node,
                "path": list(state.path),
                "predicted_total_cost": score,
                "probability": weight / normalizer,
                "predicted_rank": ranks[index],
            }
            for index, (state, score, weight) in enumerate(zip(candidates, scores, weights))
        ],
    }


class RootChoiceTracker:
    """Attribuisce le estrazioni alla prima scelta dopo il percorso iniziale."""

    def __init__(self, initial_state, distribution):
        self.prefix_length = len(initial_state.path)
        self.distribution = distribution
        self.examined = {row["action"]: 0 for row in distribution["alternatives"]}
        self.best_costs = {action: None for action in self.examined}
        self.diversification_events = []
        self.improvements = []

    def action_of(self, state):
        if len(state.path) > self.prefix_length:
            return state.path[self.prefix_length]
        return None

    def selected(self, state, step, diversified=False):
        action = self.action_of(state)
        if action in self.examined:
            self.examined[action] += 1
        if diversified:
            self.diversification_events.append({
                "step": step, "path": list(state.path), "cost": state.cost,
                "root_action": action,
            })

    def tour(self, state, step, improved):
        action = self.action_of(state)
        if action in self.best_costs:
            current = self.best_costs[action]
            self.best_costs[action] = state.cost if current is None else min(current, state.cost)
        if improved:
            self.improvements.append({
                "step": step, "best_cost": state.cost, "path": list(state.path),
                "root_action": action,
            })

    def summarize(self, stack, best_cost):
        active_counts = {action: 0 for action in self.examined}
        for state in stack:
            if state.cost >= best_cost:
                continue
            action = self.action_of(state)
            if action is None:
                # Budget zero: il padre non espanso rappresenta tutti i suoi figli.
                for candidate in active_counts:
                    active_counts[candidate] += 1
            else:
                active_counts[action] += 1
        alternatives = [
            dict(row, states_examined=self.examined[row["action"]],
                 best_cost=self.best_costs[row["action"]],
                 active_pending_states=active_counts[row["action"]],
                 unresolved=active_counts[row["action"]] > 0)
            for row in self.distribution["alternatives"]
        ]
        return {
            "temperature": self.distribution["temperature"],
            "alternatives": alternatives,
            "unresolved_probability_mass": sum(
                row["probability"] for row in alternatives if row["unresolved"]
            ),
            "diversification_events": self.diversification_events,
            "improvements": self.improvements,
        }
