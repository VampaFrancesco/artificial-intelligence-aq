"""Confronto A/B/C e analisi offline delle prime scelte.

L'enumerazione indipendente serve esclusivamente alla valutazione: i suoi
risultati non vengono passati agli algoritmi online né al regolatore.
"""

from itertools import permutations
from math import isclose
from statistics import mean
from time import perf_counter

from ..algorithms.baseline import BranchAndBound
from ..algorithms.predictive_search import predictiveSearch
from ..algorithms.probability import RootChoiceTracker, action_distribution
from ..models.state import State
from ..models.tsp import successors
from .generate_dataset import reference_completion


def enumerate_optimum(state, matrix):
    """Riferimento indipendente dal B&B, praticabile solo su piccole istanze."""
    if len(state.unvisited) > 9:
        raise ValueError("Il riferimento esaustivo è limitato a nove consegne residue.")
    best = None
    for order in permutations(sorted(state.unvisited)):
        continuation = (state.current_node,) + order + (0,)
        cost = state.cost + sum(matrix[a][b] for a, b in zip(continuation, continuation[1:]))
        if best is None or cost < best.cost:
            best = State(path=state.path + order + (0,), unvisited=frozenset(), cost=cost)
    return best


def diagnose_choices(initial_state, matrix, distribution):
    """Confronta previsione e ricerca completa, separatamente dal budget online."""
    rows = []
    by_action = {row["action"]: row for row in distribution["alternatives"]}
    for candidate in successors(initial_state, matrix):
        optimum = enumerate_optimum(candidate, matrix)
        row = dict(by_action[candidate.current_node])
        row.update(
            exact_total_cost=optimum.cost,
            exact_path=list(optimum.path),
            prediction_residual=optimum.cost - row["predicted_total_cost"],
        )
        rows.append(row)
    rows.sort(key=lambda row: row["predicted_rank"])
    if rows:
        first_cost = rows[0]["exact_total_cost"]
        for row in rows:
            row["gain_vs_predicted_first"] = first_cost - row["exact_total_cost"]
            row["lower_half_by_prediction"] = row["predicted_rank"] > len(rows) / 2
    return rows


def run_comparison(initial_state, matrix, model_data, budgets, teacher_budget, patience=100,
                   max_seconds=None):
    certified = len(initial_state.unvisited) <= 9
    distribution = action_distribution(initial_state, matrix, model_data)
    if certified:
        reference, reference_complete, reference_stats = BranchAndBound(
            initial_state, matrix, teacher_budget
        )
        independent = enumerate_optimum(initial_state, matrix)
        if not reference_complete or reference is None:
            raise ValueError("Il B&B di riferimento deve terminare su queste piccole istanze.")
        if not isclose(reference.cost, independent.cost, rel_tol=1e-10, abs_tol=1e-9):
            raise AssertionError("B&B e riferimento indipendente non concordano.")
        independent_cost = independent.cost
        diagnostics = diagnose_choices(initial_state, matrix, distribution)
    else:
        # Su 100 consegne non avviamo enumerazione o B&B esaustivi per i riferimenti.
        reference = reference_completion(initial_state, matrix, starts=12, passes=20)
        reference_stats = None
        independent_cost = None
        diagnostics = []
    results = []
    methods = ("Branch and Bound", "Predittiva", "Regolata")
    for budget in budgets:
        for method in methods:
            observer = RootChoiceTracker(initial_state, distribution)
            started = perf_counter()
            if method == "Branch and Bound":
                best, complete, stats = BranchAndBound(initial_state, matrix, budget, observer,
                                                     max_seconds=max_seconds)
            else:
                best, complete, stats = predictiveSearch(
                    initial_state, matrix, budget, model_data,
                    patience=patience if method == "Regolata" else None,
                    observer=observer,
                    max_seconds=max_seconds,
                )
            elapsed = perf_counter() - started
            gap = None
            if best is not None and certified:
                gap = (100 * (best.cost - reference.cost) / reference.cost
                       if reference.cost else 0.0)
                if isclose(best.cost, reference.cost, rel_tol=1e-10, abs_tol=1e-9):
                    gap = 0.0
            results.append({
                "initial_path": list(initial_state.path),
                "budget": budget, "method": method,
                "time_budget_seconds": max_seconds,
                "best_cost": best.cost if best is not None else None,
                "best_path": list(best.path) if best is not None else None,
                "optimal_cost": reference.cost if certified else None, "gap_percent": gap,
                "reference_cost": reference.cost,
                "reference_is_certified_optimum": certified,
                "is_complete": complete, "elapsed_seconds": elapsed, "stats": stats,
            })
    return results, {
        "reference_cost": reference.cost,
        "reference_is_certified_optimum": certified,
        "reference_method": ("branch_and_bound_and_enumeration" if certified
                             else "nearest_neighbor_12_starts_2opt_20_passes"),
        "independent_enumeration_cost": independent_cost,
        "reference_stats": reference_stats,
        "temperature": distribution["temperature"],
        "alternatives": diagnostics,
    }


def summarize_results(results):
    """Medie descrittive: ogni istanza ha lo stesso peso all'interno del budget."""
    summary = []
    for budget in sorted({row["budget"] for row in results}):
        for method in ("Branch and Bound", "Predittiva", "Regolata"):
            rows = [row for row in results if row["budget"] == budget and row["method"] == method]
            gaps = [row["gap_percent"] for row in rows if row["gap_percent"] is not None]
            summary.append({
                "budget": budget, "method": method, "instances": len(rows),
                "tours_found": sum(row["best_cost"] is not None for row in rows),
                "mean_gap_percent": mean(gaps) if gaps else None,
                "optimal_tours_found": sum(gap == 0 for gap in gaps) if gaps else None,
                "mean_best_cost": mean(row["best_cost"] for row in rows
                                       if row["best_cost"] is not None)
                                  if any(row["best_cost"] is not None for row in rows) else None,
                "mean_unresolved_probability_mass": mean(
                    row["stats"]["root_choice"]["unresolved_probability_mass"] for row in rows
                ),
                "mean_elapsed_seconds": mean(row["elapsed_seconds"] for row in rows),
            })
    return summary
