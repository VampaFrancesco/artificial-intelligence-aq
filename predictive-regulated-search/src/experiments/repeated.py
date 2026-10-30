"""Protocollo fisso: dieci mappe nuove, due tempi, tre ripetizioni A/B/C."""

import hashlib
import json
import platform
from datetime import datetime
from math import isclose
from pathlib import Path
from statistics import mean, median
from uuid import uuid4

from .benchmark import run_comparison
from .generate_dataset import generate_locations
from ..models.state import State
from ..models.tsp import distance_matrix

METHODS = ("Branch and Bound", "Predittiva", "Regolata")


def save(path, value):
    # Scrittura atomica: una prova interrotta lascia leggibili quelle già concluse.
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def coordinates(locations):
    return [{"x": p.x, "y": p.y} for p in locations]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def validate_runs(runs, matrix):
    for run in runs:
        path = run["best_path"]
        if path is None:
            continue
        if (len(path) != len(matrix) + 1 or path[0] != 0 or path[-1] != 0
                or sorted(path[:-1]) != list(range(len(matrix)))):
            raise AssertionError("La ricerca ha restituito un giro non valido.")
        cost = sum(matrix[a][b] for a, b in zip(path, path[1:]))
        if not isclose(cost, run["best_cost"], rel_tol=1e-10, abs_tol=1e-8):
            raise AssertionError("Il costo salvato non coincide con il percorso.")


def summarize(runs):
    rows = []
    for seconds in (1, 3):
        for name in sorted({r["instance_id"] for r in runs}):
            row = {"instance_id": name, "seconds": seconds, "methods": {}}
            for method in METHODS:
                group = [r for r in runs if r["instance_id"] == name
                         and r["time_budget_seconds"] == seconds and r["method"] == method]
                if len(group) != 3:
                    raise ValueError("Servono tre ripetizioni per ogni mappa, metodo e tempo.")
                costs = [r["best_cost"] for r in group if r["best_cost"] is not None]
                # Non escludere silenziosamente fallimenti dal confronto di qualità.
                row["methods"][method] = {
                    "tours_found": len(costs),
                    "median_cost": median(costs) if len(costs) == 3 else None,
                    "min_cost": min(costs) if costs else None,
                    "max_cost": max(costs) if costs else None,
                    "median_search_seconds": median(r["stats"]["search_elapsed_seconds"] for r in group),
                    "max_search_seconds": max(r["stats"]["search_elapsed_seconds"] for r in group),
                    "median_total_seconds": median(r["elapsed_seconds"] for r in group),
                }
            a, b, c = [row["methods"][m]["median_cost"] for m in METHODS]
            row["prediction_gain_percent"] = 100 * (a - b) / a if a and b is not None else None
            row["regulation_gain_percent"] = 100 * (b - c) / b if b and c is not None else None
            row["regulation_result"] = (
                "non confrontabile" if b is None or c is None else
                "pareggio" if isclose(b, c, rel_tol=1e-9, abs_tol=1e-8) else
                "migliora" if c < b else "peggiora"
            )
            rows.append(row)
    return rows


def number(value):
    return "—" if value is None else f"{value:.3f}"


def overview(data):
    lines = ["# Esperimento su dieci mappe nuove", "",
             "Modello da 100 consegne e regolatore fissi; nessun nuovo allenamento.",
             "Ogni valore è la mediana di tre esecuzioni sulla stessa mappa.",
             "Guadagno positivo = distanza ridotta; negativo = peggioramento.",
             "Le ripetizioni misurano la variabilità temporale, non aggiungono mappe indipendenti.", ""]
    for seconds in (1, 3):
        rows = [r for r in data["summary"] if r["seconds"] == seconds]
        lines += [f"## Budget nominale: {seconds} secondo/i", "",
                  "| Mappa | Base A | Predittiva B | Regolata C | B su A % | C su B % |",
                  "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for row in rows:
            costs = [number(row["methods"][m]["median_cost"]) for m in METHODS]
            lines.append(f"| {row['instance_id']} | " + " | ".join(costs) +
                         f" | {number(row['prediction_gain_percent'])} | {number(row['regulation_gain_percent'])} |")
        counts = {key: sum(r["regulation_result"] == key for r in rows)
                  for key in ("migliora", "pareggio", "peggiora", "non confrontabile")}
        gains_b = [r["prediction_gain_percent"] for r in rows if r["prediction_gain_percent"] is not None]
        gains_c = [r["regulation_gain_percent"] for r in rows if r["regulation_gain_percent"] is not None]
        lines += ["", f"C rispetto a B: {counts['migliora']} miglioramenti, {counts['pareggio']} pareggi, "
                  f"{counts['peggiora']} peggioramenti, {counts['non confrontabile']} casi non confrontabili.",
                  f"Media dei guadagni percentuali per mappa: B su A {number(mean(gains_b) if gains_b else None)}%; "
                  f"C su B {number(mean(gains_c) if gains_c else None)}%.", "",
                  "| Metodo | Mediana del tempo di ricerca effettivo | Massimo |",
                  "| --- | ---: | ---: |"]
        for method in METHODS:
            group = [r for r in data["runs"] if r["time_budget_seconds"] == seconds and r["method"] == method]
            lines.append(f"| {method} | {median(r['stats']['search_elapsed_seconds'] for r in group):.4f} s | "
                         f"{max(r['stats']['search_elapsed_seconds'] for r in group):.4f} s |")
        lines += [""]
    lines += ["## Caso piccolo: previsione e ricerca aggiuntiva", "",
              "Caso illustrativo già individuato nelle prove precedenti; non è una nuova conferma indipendente.",
              "Per ogni prima consegna, l'enumerazione calcola il miglior giro possibile in quel ramo.",
              "Il residuo è costo esatto meno costo previsto. Questi valori sono solo diagnostici offline.", "",
              "| Prima consegna | Posizione prevista | Costo totale previsto | Miglior costo esatto | Residuo |",
              "| --- | ---: | ---: | ---: | ---: |"]
    case = data["small_case"]
    for row in case["reference"]["alternatives"]:
        lines.append(f"| {row['action']} | {row['predicted_rank']} | {row['predicted_total_cost']:.3f} | "
                     f"{row['exact_total_cost']:.3f} | {row['prediction_residual']:.3f} |")
    lines += ["", "Con 500 estrazioni:", ""]
    for run in case["runs"]:
        lines.append(f"- {run['method']}: costo {number(run['best_cost'])}, gap dall'ottimo {number(run['gap_percent'])}%.")
    last = max(case["reference"]["alternatives"], key=lambda r: r["predicted_rank"])
    action = last["action"]
    lines += ["", f"Il ramo classificato ultimo inizia dalla consegna {action}."]
    for run in case["runs"][1:]:
        tracker = run["stats"]["root_choice"]
        branch = next(r for r in tracker["alternatives"] if r["action"] == action)
        lines.append(f"- {run['method']}: {branch['states_examined']} estrazioni in quel ramo; "
                     f"miglior giro nel ramo: {number(branch['best_cost'])}.")
        for event in tracker["diversification_events"]:
            if event["root_action"] == action and len(event["path"]) == 2:
                lines.append(f"  Apertura del ramo per diversificazione al passo {event['step']}.")
        for event in tracker["improvements"]:
            if event["root_action"] == action:
                lines.append(f"  Miglioramento al passo {event['step']}: {event['best_cost']:.3f}.")
    lines += ["", "## Come leggere i risultati", "",
              "I confronti usano le stesse coordinate e lo stesso modello. L'ordine dei metodi ruota fra le "
              "ripetizioni, così ciascuno occupa una volta ogni posizione. Le ricerche vengono eseguite in sequenza.",
              "Il limite riguarda il ciclo di ricerca, incluso il monitoraggio interno. Il controllo avviene fra "
              "iterazioni: l'ultima può superare il limite. Preparazione, riferimento e statistiche finali sono esclusi.",
              "I riferimenti delle mappe grandi sono euristici, non ottimi certificati. Nessun riferimento guida la ricerca.",
              "Dieci mappe uniformi nello stesso intervallo dell'allenamento non dimostrano un vantaggio su ogni tipo di mappa.",
              "La mediana e gli intervalli delle singole prove sono nel JSON, insieme a percorsi, coordinate, "
              "modelli e tempi. Un grande residuo da solo non dimostra che un ramo meriti più ricerca.", ""]
    return "\n".join(lines)


def run_experiment(project_dir):
    data_dir = project_dir / "data"
    required = [data_dir / name for name in ("model_100.json", "model.json", "consegne_100.json", "examples.json")]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Serve {path}. Rigenera i dati/modelli prima dell'esperimento.")
    model, small_model, training, small_training = [json.loads(p.read_text()) for p in required]
    if model.get("deliveries") != 100:
        raise ValueError("Serve il modello allenato sulle mappe da 100 consegne.")
    # Scelte fissate prima di osservare gli esiti; nessuna selezione delle mappe favorevoli.
    seeds = list(range(30000, 30010))
    maps = {f"mappa_{i + 1:02d}": generate_locations(100, seed) for i, seed in enumerate(seeds)}
    known = {fingerprint(points) for points in training["instances"].values()}
    if any(fingerprint(coordinates(locations)) in known for locations in maps.values()):
        raise ValueError("Le nuove mappe non devono comparire nel dataset originale.")
    small_locations = generate_locations(6, 53)
    if fingerprint(coordinates(small_locations)) in {fingerprint(p) for p in small_training["instances"].values()}:
        raise ValueError("Il caso piccolo non deve appartenere al dataset originale.")
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S")
    folder = project_dir / "results" / "esperimenti" / f"{stamp}_{uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=False)
    source_hashes = {str(p.relative_to(project_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted((project_dir / "src").rglob("*.py"))}
    data = {
        "status": "running", "started_at": datetime.now().astimezone().isoformat(),
        "configuration": {"deliveries": 100, "map_count": 10, "seconds": [1, 3], "repetitions": 3,
                          "patience": 100, "map_seeds": seeds, "small_case_seed": 53,
                          "small_case_previously_selected": True,
                          "method_order": "rotate_once_per_repetition_and_map",
                          "python_version": platform.python_version(), "platform": platform.platform(),
                          "processor": platform.processor(), "source_sha256": source_hashes,
                          "model_sha256": fingerprint(model), "small_model_sha256": fingerprint(small_model)},
        "model_parameters": model, "small_model_parameters": small_model,
        "instances": {name: coordinates(locations) for name, locations in maps.items()},
        "runs": [], "references": {},
    }
    result_path = folder / "risultati.json"
    save(result_path, data)
    print(f"Esperimento: 10 mappe nuove, 1 e 3 secondi, 3 ripetizioni.\nSalvataggio: {folder}", flush=True)
    for index, (name, locations) in enumerate(maps.items()):
        matrix = distance_matrix(locations)
        initial = State(path=(0,), unvisited=frozenset(range(1, len(matrix))), cost=0.0)
        for seconds in (1, 3):
            for repetition in range(3):
                shift = (index + repetition) % 3
                order = METHODS[shift:] + METHODS[:shift]
                runs, reference = run_comparison(initial, matrix, model, (None,), 100000,
                                                max_seconds=seconds, method_order=order)
                validate_runs(runs, matrix)
                for run in runs:
                    run.update(instance_id=name, repetition=repetition + 1,
                               execution_order=list(order))
                data["runs"].extend(runs)
                data["references"][name] = reference
                save(result_path, data)
                print(f"{name}: {seconds}s, ripetizione {repetition + 1}/3 completata "
                      f"({len(data['runs'])}/180 ricerche).", flush=True)
    matrix = distance_matrix(small_locations)
    initial = State(path=(0,), unvisited=frozenset(range(1, 7)), cost=0.0)
    runs, reference = run_comparison(initial, matrix, small_model, (500,), 100000)
    validate_runs(runs, matrix)
    data["small_case"] = {"coordinates": coordinates(small_locations), "runs": runs, "reference": reference}
    data["summary"] = summarize(data["runs"])
    data.update(status="completed", completed_at=datetime.now().astimezone().isoformat())
    save(result_path, data)
    report = folder / "riepilogo.md"
    report.write_text(overview(data), encoding="utf-8")
    print(f"\nProve completate. Riepilogo: {report}", flush=True)
    return folder
