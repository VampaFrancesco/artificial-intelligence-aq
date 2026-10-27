"""Avvio del progetto: generazione dei dati, addestramento o confronto delle ricerche."""

import argparse
import json
import platform
from math import isfinite
from pathlib import Path

from .experiments.benchmark import run_comparison, summarize_results
from .algorithms.predictor import (
    extract_features,
    load_model_parameters,
    predict_remaining_cost,
    train_predictor,
)
from .experiments.generate_dataset import collect_examples, generate_locations, generate_large_dataset
from .models.node import Node
from .models.state import State
from .models.tsp import distance_matrix
from .utils.loader import load_location
from .utils.history import save_personal_result


# CONFIGURAZIONE: modifica questi valori per scegliere cosa eseguire.
# "generate": crea examples.json; "train": addestra e salva il modello;
# "compare": confronta A/B/C; "all": riproduce tutte le fasi.
MODE = "compare"

# True: piccole mappe disegnate a mano per capire l'allenamento.
# False: torna alle istanze casuali dell'esperimento precedente.
USE_TEACHING_DATA = False

N_DELIVERIES = 6
DATASET_SEEDS = range(42, 52)
TEACHER_BUDGET = 100_000  # Budget offline, per ottenere i target del dataset.

# Queste istanze sono escluse dall'addestramento e usate per la verifica.
TEST_INSTANCE_IDS = (
    ("test_triangolo", "test_irregolare")
    if USE_TEACHING_DATA
    else ("istanza_seed_50", "istanza_seed_51")
)
SEARCH_BUDGETS = ((5, 10, 20, 50) if USE_TEACHING_DATA else (50, 100, 200, 500))
REGULATOR_PATIENCE = 100
SEARCH_SECONDS = None  # Se impostato da --seconds, sostituisce il budget di stati.

# Stato da cui iniziare ogni ricerca: deposito, nessuna consegna effettuata.
# Per ripetere la prova con la prima consegna gia' scelta, usa (0, 2).
# Costo e consegne rimaste vengono ricavati automaticamente da questo percorso.
START_PATH = (0,)

# I percorsi dipendono dalla posizione del progetto, non dalla cartella del terminale.
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
RESULTS_DIR = PROJECT_DIR / "results"
if USE_TEACHING_DATA:
    # Dataset, modello e risultati didattici hanno una cartella separata.
    DATA_DIR = DATA_DIR / "didattico"
    RESULTS_DIR = RESULTS_DIR / "didattico"


def save_json(file_path, data):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def dataset_path():
    return DATA_DIR / ("consegne_100.json" if N_DELIVERIES == 100 else "examples.json")


def model_path():
    return DATA_DIR / ("model_100.json" if N_DELIVERIES == 100 else "model.json")


def dataset_split(dataset):
    if "splits" in dataset:
        train_ids = set(dataset["splits"]["train"])
        test_ids = set(dataset["splits"]["test"])
    else:
        test_ids = set(TEST_INSTANCE_IDS)
        train_ids = set(dataset["instances"]) - test_ids
    if (not train_ids or not test_ids or train_ids & test_ids
            or train_ids | test_ids != set(dataset["instances"])):
        raise ValueError("Le mappe di allenamento e prova devono essere distinte e coprire il dataset.")
    return train_ids, test_ids


def load_dataset():
    file_path = dataset_path()
    if not file_path.exists():
        raise FileNotFoundError(
            f'Dataset mancante: {file_path}. Usa --mode generate con la stessa dimensione.'
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
    """Genera coordinate e target; su 100 consegne usa un insegnante approssimato."""
    if N_DELIVERIES == 100:
        dataset = generate_large_dataset(progress=lambda message: print(message, flush=True))
        save_json(dataset_path(), dataset)
        print(f"Dataset salvato in {dataset_path()}: 12 mappe per allenare e 3 per provare.")
        print("Ogni mappa ha 100 consegne più il deposito; i target non sono ottimi certificati.")
        return
    dataset = {"instances": {}, "examples": []}

    if USE_TEACHING_DATA:
        # Queste coordinate sono scelte a mano e si possono leggere e modificare.
        with open(DATA_DIR / "instances.json", "r", encoding="utf-8") as file:
            dataset["instances"] = json.load(file)
    else:
        for seed in DATASET_SEEDS:
            locations = generate_locations(n_deliveries=N_DELIVERIES, seed=seed)
            dataset["instances"][f"istanza_seed_{seed}"] = [
                {"x": node.x, "y": node.y} for node in locations
            ]

    for instance_id, coordinates in dataset["instances"].items():
        locations = [Node(x=point["x"], y=point["y"]) for point in coordinates]
        examples = collect_examples(
            locations,
            instance_id=instance_id,
            max_states=TEACHER_BUDGET,
            max_depth=len(locations) - 1,
        )
        dataset["examples"].extend(examples)
        print(f"{instance_id}: {len(examples)} esempi raccolti")

    save_json(dataset_path(), dataset)
    print(f"Dataset salvato: {len(dataset['examples'])} esempi")


def mean_absolute_error(predicted_costs, actual_costs):
    total_error = 0
    for predicted, actual in zip(predicted_costs, actual_costs):
        total_error += abs(predicted - actual)
    return total_error / len(actual_costs)


def train_and_evaluate(dataset):
    """Fase offline: prepara le feature, addestra e valuta sulle istanze escluse."""
    matrices = build_matrices(dataset)
    train_ids, test_ids = dataset_split(dataset)
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

        if instance_id in test_ids:
            test_features.append(features)
            test_costs.append(target)
        elif instance_id in train_ids:
            train_features.append(features)
            train_costs.append(target)
        else:
            raise ValueError(f"Esempio di una mappa assente dal dataset: {instance_id}")

    if not train_features or not test_features:
        raise ValueError("Servono istanze distinte per addestramento e verifica.")

    if N_DELIVERIES != 100:
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
    import sklearn
    metrics = {
        "training_instances": sorted(train_ids),
        "test_instances": sorted(test_ids),
        "training_examples": len(train_features),
        "test_examples": len(test_features),
        "model_mae": model_error,
        "constant_mae": constant_error,
        "python_version": platform.python_version(),
        "scikit_learn_version": sklearn.__version__,
        "target_metadata": dataset.get("metadata", {"targets_are_certified": True}),
    }
    if N_DELIVERIES == 100:
        model_data.update(deliveries=100, training_metrics=metrics)
    else:
        save_json(DATA_DIR / "training_metrics.json", metrics)
    save_json(model_path(), model_data)

    print(f"Esempi per addestrare: {len(train_features)}")
    print(f"Esempi per verificare: {len(test_features)}")
    print(f"Errore assoluto medio del predittore: {model_error:.3f}")
    print(f"Errore assoluto medio della previsione costante: {constant_error:.3f}")
    print(f"Parametri salvati in {model_path()}")

    # Controlla la lettura dei parametri sullo stesso esempio usato da model.predict.
    loaded_parameters = load_model_parameters(model_path())
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


def compare_searches(dataset, input_file=None):
    """Confronta A/B/C; riferimenti e diagnosi non consumano il budget online."""
    model_file = model_path()
    if not model_file.exists():
        raise FileNotFoundError(
            f"Modello mancante: {model_file}. Per rigenerare dataset e modello usa "
            f"python3 -m src.main --deliveries {N_DELIVERIES} --mode all, senza --input."
        )
    model_data = load_model_parameters(model_file)
    if model_data.get("deliveries", N_DELIVERIES) != N_DELIVERIES:
        raise ValueError("Il modello non è stato allenato per questa dimensione delle mappe.")
    matrices = build_matrices(dataset)
    if input_file is not None:
        test_instance_ids = list(matrices)
        actual_deliveries = len(next(iter(matrices.values()))) - 1
        print(f"Mappa personale: {actual_deliveries} consegne più il deposito.")
        print(f"Modello usato: {model_file.name}, allenato su mappe da {N_DELIVERIES} consegne.")
        if actual_deliveries != N_DELIVERIES:
            print("Nota: il numero di consegne differisce dall'allenamento; l'accuratezza qui non è verificata.")
    else:
        _, test_ids = dataset_split(dataset)
        test_instance_ids = sorted(test_ids)
    if input_file is None and not USE_TEACHING_DATA and N_DELIVERIES != 100:
        for seed in (52, 53):
            instance_id = f"istanza_seed_{seed}"
            locations = generate_locations(n_deliveries=N_DELIVERIES, seed=seed)
            matrices[instance_id] = distance_matrix(locations)
            test_instance_ids.append(instance_id)

    results = []
    diagnostics = {}
    print(f"Percorso iniziale: {START_PATH}")
    print("Costi totali, incluso il ritorno al deposito. Rho: massa ancora irrisolta.")
    for instance_id in test_instance_ids:
        initial_state = make_initial_state(matrices[instance_id])
        runs, diagnostic = run_comparison(
            initial_state, matrices[instance_id], model_data, SEARCH_BUDGETS,
            TEACHER_BUDGET, REGULATOR_PATIENCE,
            max_seconds=SEARCH_SECONDS,
        )
        diagnostics[instance_id] = diagnostic
        reference_label = ("Ottimo" if diagnostic["reference_is_certified_optimum"]
                           else "Riferimento approssimato")
        print(f"\nMappa: {instance_id} | {reference_label}: {diagnostic['reference_cost']:.6f}")
        print(f"{'Budget':>6}  {'Metodo':<17} {'Costo totale':>13} {'Gap %':>9} {'Rho':>7} {'Divers.':>7}")
        for run in runs:
            run["instance_id"] = instance_id
            results.append(run)
            cost = f"{run['best_cost']:.3f}" if run["best_cost"] is not None else "Nessun giro"
            gap = f"{run['gap_percent']:.2f}" if run["gap_percent"] is not None else "-"
            stats = run["stats"]
            rho = stats["root_choice"]["unresolved_probability_mass"]
            budget_label = f"{SEARCH_SECONDS:g}s" if SEARCH_SECONDS is not None else str(run["budget"])
            print(f"{budget_label:>6}  {run['method']:<17} {cost:>13} {gap:>9} "
                  f"{rho:>7.3f} {stats.get('diversification_steps', 0):>7}")

    config = {
        "deliveries": actual_deliveries if input_file is not None else N_DELIVERIES,
        "model_training_deliveries": N_DELIVERIES,
        "dataset_path": (str(input_file) if input_file is not None
                         else str(dataset_path().relative_to(PROJECT_DIR))),
        "teaching_data": USE_TEACHING_DATA, "initial_path": list(START_PATH),
        "budgets": list(SEARCH_BUDGETS), "regulator_patience": REGULATOR_PATIENCE,
        "search_seconds": SEARCH_SECONDS,
        "teacher_budget": TEACHER_BUDGET, "test_instances": test_instance_ids,
        "temperature_rule": "mean_pairwise_distance_or_1_if_zero",
        "probability_meaning": "fixed_preference_over_next_deliveries",
        "timing": "single_run_including_monitoring_excluding_offline_references_and_distribution",
        "python_version": platform.python_version(),
        "model_parameters": model_data,
    }
    if input_file is not None:
        output = RESULTS_DIR / "mappa_personale.json"
        archived, overview = save_personal_result(RESULTS_DIR, {
            "configuration": config, "instances": dataset["instances"],
            "runs": results, "references": diagnostics,
        })
        found = [row for row in results if row["best_cost"] is not None]
        if found:
            best = min(found, key=lambda row: row["best_cost"])
            print(f"\nMiglior giro trovato ({best['method']}, distanza {best['best_cost']:.3f}):")
            print(" -> ".join(str(node) for node in best["best_path"]))
        print(f"\nRisultati salvati in {output}")
        print(f"Copia completa della prova: {archived}")
        print(f"Tabella di confronto: {overview}")
    elif N_DELIVERIES == 100:
        output = RESULTS_DIR / ("consegne_100_tempo.json" if SEARCH_SECONDS is not None
                                else "consegne_100.json")
        save_json(output, {"configuration": config, "runs": results,
                           "references": diagnostics, "summary": summarize_results(results)})
        print(f"\nRisultati salvati in {output}")
    else:
        save_json(RESULTS_DIR / "search_comparison.json", results)
        save_json(RESULTS_DIR / "choice_diagnostics.json", diagnostics)
        save_json(RESULTS_DIR / "summary.json", summarize_results(results))
        save_json(RESULTS_DIR / "experiment_config.json", config)
        print(f"\nRisultati, diagnosi e configurazione salvati in {RESULTS_DIR}")


def main(argv=None):
    global USE_TEACHING_DATA, TEST_INSTANCE_IDS, DATA_DIR, RESULTS_DIR
    global SEARCH_BUDGETS, START_PATH, REGULATOR_PATIENCE
    global N_DELIVERIES
    global SEARCH_SECONDS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("generate", "train", "compare", "all"), default=MODE)
    parser.add_argument("--deliveries", type=int, choices=(6, 100), default=N_DELIVERIES,
                        help="Dimensione del dataset/modello; con --input sceglie il modello allenato.")
    parser.add_argument("--input", type=Path, help="Mappa personale JSON con depot e deliveries.")
    parser.add_argument("--teaching", action=argparse.BooleanOptionalAction, default=USE_TEACHING_DATA,
                        help="Usa le mappe didattiche separate.")
    parser.add_argument("--budgets", type=int, nargs="+", help="Budget online di estrazioni.")
    parser.add_argument("--seconds", type=float, help="Tempo di ricerca per metodo, al posto degli stati.")
    parser.add_argument("--patience", type=int, default=REGULATOR_PATIENCE)
    parser.add_argument("--start-path", type=int, nargs="+", default=START_PATH)
    args = parser.parse_args(argv)
    if args.seconds is not None and (not isfinite(args.seconds) or args.seconds <= 0):
        parser.error("Il tempo deve essere finito e positivo.")
    if args.seconds is not None and args.budgets is not None:
        parser.error("Scegli un budget di stati oppure un limite di tempo.")
    if args.seconds is not None and args.deliveries != 100 and args.input is None:
        parser.error("Il confronto a tempo è disponibile per il dataset da 100 consegne.")
    if args.input is not None and (args.mode != "compare" or args.teaching):
        parser.error("Usa --input per la ricerca (--mode compare), senza --teaching.")
    SEARCH_SECONDS = args.seconds
    if args.teaching and args.deliveries == 100:
        parser.error("Le mappe didattiche hanno quattro consegne; usa --deliveries 100 senza --teaching.")
    if args.patience <= 0 or (args.budgets is not None and any(b < 0 for b in args.budgets)):
        parser.error("La soglia deve essere positiva e i budget non negativi.")
    if args.deliveries == 100 or args.input is not None:
        default_budgets = (5000,)
    else:
        default_budgets = SEARCH_BUDGETS if args.teaching == USE_TEACHING_DATA else (
            (5, 10, 20, 50) if args.teaching else (50, 100, 200, 500)
        )
    N_DELIVERIES = args.deliveries
    USE_TEACHING_DATA = args.teaching
    START_PATH = tuple(args.start_path)
    REGULATOR_PATIENCE = args.patience
    TEST_INSTANCE_IDS = (("test_triangolo", "test_irregolare") if args.teaching
                         else ("istanza_seed_50", "istanza_seed_51"))
    DATA_DIR = PROJECT_DIR / "data"
    RESULTS_DIR = PROJECT_DIR / "results"
    if args.teaching:
        DATA_DIR /= "didattico"
        RESULTS_DIR /= "didattico"
    SEARCH_BUDGETS = tuple(args.budgets) if args.budgets is not None else default_budgets
    if SEARCH_SECONDS is not None:
        SEARCH_BUDGETS = (None,)
    if args.mode in ("generate", "all"):
        generate_dataset()
    if args.mode in ("train", "all"):
        train_and_evaluate(load_dataset())
    if args.mode in ("compare", "all"):
        if args.input is not None:
            try:
                locations = load_location(args.input)
            except (OSError, ValueError) as error:
                parser.error(str(error))
            dataset = {"instances": {"mappa_personale": [
                {"x": node.x, "y": node.y} for node in locations
            ]}}
            compare_searches(dataset, input_file=args.input.resolve())
        else:
            compare_searches(load_dataset())


if __name__ == "__main__":
    main()
