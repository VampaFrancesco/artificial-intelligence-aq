"""Conserva ogni prova personale con coordinate, modello e risultati."""

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo


LOCAL_TIME = ZoneInfo("Europe/Rome")


def fingerprint(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def write_json(path, value):
    with path.open("w", encoding="utf-8") as file:
        json.dump(value, file, indent=2, ensure_ascii=False, allow_nan=False)


def archive_result(results_dir, result, saved_at=None, source="execution"):
    folder = Path(results_dir) / "storico"
    folder.mkdir(parents=True, exist_ok=True)
    moment = saved_at or datetime.now(LOCAL_TIME)
    config = result["configuration"]
    parameters = config["model_parameters"]
    model_formula = {key: parameters[key] for key in ("weights", "intercept")}
    while True:
        experiment_id = f"{moment:%Y-%m-%d_%H-%M-%S}_{config['deliveries']}consegne_{uuid4().hex[:8]}"
        path = folder / f"{experiment_id}.json"
        snapshot = dict(result, experiment_id=experiment_id,
                        saved_at=moment.isoformat(), archive_source=source,
                        map_hash=fingerprint(result["instances"]),
                        model_hash=fingerprint(model_formula))
        try:
            # La modalità x impedisce di sovrascrivere anche in caso di collisione.
            with path.open("x", encoding="utf-8") as file:
                json.dump(snapshot, file, indent=2, ensure_ascii=False, allow_nan=False)
        except FileExistsError:
            continue
        return snapshot, path


def preserve_latest(results_dir):
    """Recupera anche il risultato precedente, se non ha ancora una copia storica."""
    results_dir = Path(results_dir)
    latest = results_dir / "mappa_personale.json"
    if not latest.exists():
        return None
    result = json.loads(latest.read_text(encoding="utf-8"))
    experiment_id = result.get("experiment_id", "")
    safe_id = isinstance(experiment_id, str) and experiment_id and all(
        char.isascii() and (char.isalnum() or char in "-_") for char in experiment_id
    )
    existing = results_dir / "storico" / f"{experiment_id}.json" if safe_id else None
    if existing is not None and existing.is_file():
        return existing
    # Per i vecchi file la data è quella dell'ultima modifica, non un'ora inventata.
    moment = (datetime.fromisoformat(result["saved_at"]) if result.get("saved_at")
              else datetime.fromtimestamp(latest.stat().st_mtime, LOCAL_TIME))
    snapshot, archived = archive_result(results_dir, result, moment, "previous_result_file")
    write_json(latest, snapshot)
    return archived


def write_overview(results_dir):
    results_dir = Path(results_dir)
    rows = []
    for path in sorted((results_dir / "storico").glob("*.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        config = result["configuration"]
        groups = {}
        for run in result["runs"]:
            key = (run["budget"], run.get("time_budget_seconds", config.get("search_seconds")))
            groups.setdefault(key, {})[run["method"]] = run
        for (states, seconds), methods in groups.items():
            values = [methods.get(name, {}).get("best_cost")
                      for name in ("Branch and Bound", "Predittiva", "Regolata")]
            costs = [f"{value:.3f}" if value is not None else "-" for value in values]
            gain = "-"
            if values[1] is not None and values[2] is not None:
                if values[1] > 0:
                    gain = f"{100 * (values[1] - values[2]) / values[1]:+.2f}%"
                elif values[1] == values[2] == 0:
                    gain = "0.00%"
            when = datetime.fromisoformat(result["saved_at"]).astimezone(LOCAL_TIME)
            label = f"[{when:%d/%m/%Y %H:%M:%S}](storico/{path.name})"
            budget = f"{seconds:g} s" if seconds is not None else f"{states} stati"
            rows.append("| " + " | ".join([
                label, str(config["deliveries"]), str(config["model_training_deliveries"]),
                budget, *costs, gain,
            ]) + " |")
    source = """# Confronto delle prove personali

Ogni riga è un'esecuzione. Il link apre il salvataggio completo con coordinate,
parametri del modello e risultati. La colonna Modello indica il numero di
consegne delle mappe usate per allenarlo.

I costi assoluti di mappe diverse non sono direttamente confrontabili.
C rispetto a B misura la riduzione di distanza della regolata rispetto alla
predittiva sulla stessa mappa: positivo significa un giro più corto.
Ripetere una mappa è una nuova esecuzione, non una nuova mappa indipendente;
ogni salvataggio contiene le impronte della mappa e del modello per riconoscerle.

| Data e ora | Consegne | Modello | Budget | Base | Predittiva | Regolata | C rispetto a B |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
"""
    output = results_dir / "confronto_prove.md"
    output.write_text(source + "\n".join(rows) + "\n", encoding="utf-8")
    return output


def save_personal_result(results_dir, result):
    results_dir = Path(results_dir)
    preserve_latest(results_dir)
    snapshot, archived = archive_result(results_dir, result)
    write_json(results_dir / "mappa_personale.json", snapshot)
    overview = write_overview(results_dir)
    return archived, overview
