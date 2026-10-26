"""Avvio del progetto: generazione dei dati, addestramento o confronto delle ricerche."""

import json
from pathlib import Path

from .algorithms.baseline import BranchAndBound
from .algorithms.predictive_search import predictiveSearch
from .algorithms.predictor import (
    extract_features,
    load_model_parameters,
    predict_remaining_cost,
    train_predictor,
)
from .experiments.generate_dataset import collect_examples, generate_locations
from .models.node import Node
from .models.state import State
from .models.tsp import distance_matrix


# CONFIGURAZIONE: modifica questi valori per scegliere cosa eseguire.
# "generate": crea examples.json; "train": addestra e salva il modello;
# "compare": legge i file esistenti e confronta le due ricerche.
MODE = "compare"

N_DELIVERIES = 6
DATASET_SEEDS = range(42, 52)
TEACHER_BUDGET = 100_000  # Budget offline, per ottenere i target del dataset.

# Queste istanze sono escluse dall'addestramento e usate per la verifica.
TEST_INSTANCE_IDS = ("istanza_seed_50", "istanza_seed_51")
SEARCH_BUDGETS = (50, 100, 200, 500)  # Budget online, uguale per i due metodi.

# Stato da cui iniziare ogni ricerca: deposito, nessuna consegna effettuata.
# Per ripetere la prova con la prima consegna gia' scelta, usa (0, 2).
# Costo e consegne rimaste vengono ricavati automaticamente da questo percorso.
START_PATH = (0,)

# I percorsi dipendono dalla posizione del progetto, non dalla cartella del terminale.
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
RESULTS_DIR = PROJECT_DIR / "results"


def save_json(file_path, data):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def load_dataset():
    file_path = DATA_DIR / "examples.json"
    if not file_path.exists():
        raise FileNotFoundError(
            'Dataset mancante: esegui prima con MODE = "generate".'
        )
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def build_matrices(dataset):
    """Calcola una sola matrice per istanza, da riutilizzare per tutti i suoi stati."""
    matrices = {}
    for instance_id, coordinates in dataset["instances"].items():
        locations = [Node(x=point["x"], y=point["y"]) for point in coordinates]
        matrices[instance_id] = distance_matrix(locations)
    return matrices


def generate_dataset():
    """Fase offline: genera le istanze e calcola i target con il B&B insegnante."""
    dataset = {"instances": {}, "examples": []}

    for seed in DATASET_SEEDS:
        instance_id = f"istanza_seed_{seed}"
        locations = generate_locations(n_deliveries=N_DELIVERIES, seed=seed)
        dataset["instances"][instance_id] = [
            {"x": node.x, "y": node.y} for node in locations
        ]
        examples = collect_examples(
            locations,
            instance_id=instance_id,
            max_states=TEACHER_BUDGET,
            max_depth=N_DELIVERIES,
        )
        dataset["examples"].extend(examples)
        print(f"{instance_id}: {len(examples)} esempi raccolti")

    save_json(DATA_DIR / "examples.json", dataset)
    print(f"Dataset salvato: {len(dataset['examples'])} esempi")


def mean_absolute_error(predicted_costs, actual_costs):
    total_error = 0
    for predicted, actual in zip(predicted_costs, actual_costs):
        total_error += abs(predicted - actual)
    return total_error / len(actual_costs)


def train_and_evaluate(dataset):
    """Fase offline: prepara le feature, addestra e valuta sulle istanze escluse."""
    matrices = build_matrices(dataset)
    prepared_data = {"features": [], "target_costs": [], "instance_ids": []}
    train_features = []
    train_costs = []
    test_features = []
    test_costs = []

    for example in dataset["examples"]:
        instance_id = example["instance_id"]
        state_data = example["state"]
        state = State(
            path=tuple(state_data["path"]),
            unvisited=frozenset(state_data["unvisited"]),
            cost=state_data["cost"],
        )
        features = extract_features(state, matrices[instance_id])
        target = example["target_cost_to_go"]
        prepared_data["features"].append(features)
        prepared_data["target_costs"].append(target)
        prepared_data["instance_ids"].append(instance_id)

        if instance_id in TEST_INSTANCE_IDS:
            test_features.append(features)
            test_costs.append(target)
        else:
            train_features.append(features)
            train_costs.append(target)

    if not train_features or not test_features:
        raise ValueError("Servono istanze distinte per addestramento e verifica.")

    save_json(DATA_DIR / "result.json", prepared_data)
    model = train_predictor(train_features, train_costs)
    predicted_costs = model.predict(test_features)
    model_error = mean_absolute_error(predicted_costs, test_costs)

    constant_prediction = sum(train_costs) / len(train_costs)
    constant_costs = [constant_prediction for _ in test_costs]
    constant_error = mean_absolute_error(constant_costs, test_costs)

    model_data = {
        "weights": model.coef_.tolist(),
        "intercept": float(model.intercept_),
    }
    save_json(DATA_DIR / "model.json", model_data)

    print(f"Esempi per addestrare: {len(train_features)}")
    print(f"Esempi per verificare: {len(test_features)}")
    print(f"Errore assoluto medio del predittore: {model_error:.3f}")
    print(f"Errore assoluto medio della previsione costante: {constant_error:.3f}")
    print("Parametri salvati in data/model.json")

    # Controlla la lettura dei parametri sullo stesso esempio usato da model.predict.
    loaded_parameters = load_model_parameters(DATA_DIR / "model.json")
    loaded_prediction = predict_remaining_cost(test_features[0], loaded_parameters)
    print(
        f"Prima previsione: {predicted_costs[0]:.6f}; "
        f"dopo la lettura del file: {loaded_prediction:.6f}"
    )


def make_initial_state(matrix):
    """Costruisce uno stato coerente con START_PATH e con la matrice dell'istanza."""
    if not START_PATH or START_PATH[0] != 0:
        raise ValueError("START_PATH deve iniziare dal deposito 0.")
    if len(set(START_PATH)) != len(START_PATH):
        raise ValueError("START_PATH non deve ripetere nodi: il ritorno lo aggiunge la ricerca.")
    if any(node < 0 or node >= len(matrix) for node in START_PATH):
        raise ValueError("START_PATH contiene un nodo assente dall'istanza.")

    cost = 0.0
    for departure, arrival in zip(START_PATH, START_PATH[1:]):
        cost += matrix[departure][arrival]

    return State(
        path=START_PATH,
        unvisited=frozenset(range(1, len(matrix))) - set(START_PATH),
        cost=cost,
    )


def compare_searches(dataset):
    """Fase online: confronta le ricerche con lo stesso stato e budget di estrazioni."""
    model_path = DATA_DIR / "model.json"
    if not model_path.exists():
        raise FileNotFoundError('Modello mancante: esegui prima con MODE = "train".')
    model_data = load_model_parameters(model_path)
    matrices = build_matrices(dataset)
    results = []

    print(f"Percorso iniziale: {START_PATH}")
    print("I costi stampati sono totali, compreso il ritorno al deposito.")

    for instance_id in TEST_INSTANCE_IDS:
        matrix = matrices[instance_id]
        initial_state = make_initial_state(matrix)
        reference_best, reference_complete, reference_stats = BranchAndBound(
            initial_state, matrix, TEACHER_BUDGET
        )

        optimal_cost = None
        if reference_complete and reference_best is not None:
            optimal_cost = reference_best.cost

        print(f"\nIstanza: {instance_id} | Costo gia' percorso: {initial_state.cost:.3f}")
        if optimal_cost is not None:
            print(f"Costo ottimo di riferimento: {optimal_cost:.3f}")
        else:
            print("Riferimento non completato: divario dall'ottimo non disponibile.")
        print(
            f"{'Budget':>6}  {'Metodo':<17} {'Costo totale':>13}  "
            f"{'Completa':<8} {'Esaminati':>9} {'Gap %':>9}"
        )

        for budget in SEARCH_BUDGETS:
            # Ogni chiamata riparte dallo stesso stato, con una propria pila di ricerca.
            runs = [
                ("Branch and Bound", BranchAndBound(initial_state, matrix, budget)),
                ("Predittiva", predictiveSearch(initial_state, matrix, budget, model_data)),
            ]
            for method, (best_state, is_complete, stats) in runs:
                # Il divario e' disponibile solo con un giro e un ottimo certificato.
                gap_percent = None
                if best_state is not None and optimal_cost is not None:
                    if optimal_cost > 0:
                        gap_percent = 100 * (best_state.cost - optimal_cost) / optimal_cost
                    elif best_state.cost == 0:
                        gap_percent = 0.0
                gap_label = f"{gap_percent:.2f}%" if gap_percent is not None else "-"

                # Nessun giro trovato e ricerca incompleta sono due situazioni diverse.
                cost_label = f"{best_state.cost:.3f}" if best_state is not None else "Nessun giro"
                complete_label = "si" if is_complete else "no"
                print(
                    f"{budget:>6}  {method:<17} {cost_label:>13}  "
                    f"{complete_label:<8} {stats['states_examined']:>9} {gap_label:>9}"
                )
                results.append({
                    "instance_id": instance_id,
                    "initial_path": list(initial_state.path),
                    "budget": budget,
                    "method": method,
                    "best_cost": best_state.cost if best_state is not None else None,
                    "best_path": list(best_state.path) if best_state is not None else None,
                    "optimal_cost": optimal_cost,
                    "gap_percent": gap_percent,
                    "is_complete": is_complete,
                    "stats": stats,
                })

    save_json(RESULTS_DIR / "search_comparison.json", results)
    print("\nRisultati e statistiche salvati in results/search_comparison.json")


def main():
    if MODE == "generate":
        generate_dataset()
    elif MODE == "train":
        train_and_evaluate(load_dataset())
    elif MODE == "compare":
        compare_searches(load_dataset())
    else:
        raise ValueError('MODE deve essere "generate", "train" oppure "compare".')


if __name__ == "__main__":
    main()
