# import os

# from .experiments.generate_dataset import collect_examples
# from .utils.loader import load_location


# # Configurazione della raccolta: un budget B&B per ogni stato parziale.
# file_path = os.getenv("file_path", "data/data.json")
# instance_id = "istanza_001"
# max_states = 100_000

# # Legge le coordinate dal JSON e le converte in oggetti Node.
# locations = load_location(file_path)

# print("RACCOLTA DEGLI ESEMPI", flush=True)
# print(f"  File: {file_path}")
# print(f"  Consegne: {len(locations) - 1}")
# print(f"  Budget B&B per esempio: {max_states}", flush=True)

# # Matrice, stato iniziale e ricerche sono gestiti da collect_examples.
# dataset = collect_examples(
#     locations,
#     instance_id=instance_id,
#     max_states=max_states,
# )

# print(f"\nEsempi raccolti: {len(dataset)}")

# for example in dataset:
#     print(
#         f"Percorso: {example['state']['path']}"
#         f" | Costo rimanente: {example['target_cost_to_go']:.3f}"
#     )

# # Ogni prima mossa produce un esempio solo se il target è certificato.
# skipped_examples = len(locations) - 1 - len(dataset)
# if skipped_examples > 0:
#     print(f"Esempi esclusi perché il target non è certificato: {skipped_examples}")



# from .experiments.generate_dataset import (
#     collect_examples,
#     generate_locations,
# )


# seed = 42
# max_states = 100_000

# locations = generate_locations(
#     n_deliveries=6,
#     seed=seed,
# )

# print("RACCOLTA DEGLI ESEMPI")
# print(f"  Origine: coordinate generate con seed {seed}")
# print(f"  Consegne: {len(locations) - 1}")
# print(f"  Budget B&B per esempio: {max_states}")

# dataset = collect_examples(
#     locations,
#     instance_id=f"istanza_seed_{seed}",
#     max_states=max_states,
# )

# print(f"\nEsempi raccolti: {len(dataset)}")

# for example in dataset:
#     print(
#         f"Percorso: {example['state']['path']}"
#         f" | Costo rimanente: {example['target_cost_to_go']:.3f}"
#     )





import json

from .experiments.generate_dataset import (
    collect_examples,
    generate_locations,
)

from .algorithms.predictor import extract_features
from .models.state import State
from .models.tsp import distance_matrix
from .models.node import Node


# Budget del B&B insegnante per calcolare il target di ciascun esempio.
max_states = 100_000

# instances conserva le coordinate di ogni problema; examples i suoi stati e target.
dataset = {
    "instances": {},
    "examples": [],
}

# Ogni seed produce un'istanza riproducibile: qui generiamo 10 problemi diversi.
for seed in range(42, 52):
    instance_id = f"istanza_seed_{seed}"

    locations = generate_locations(
        n_deliveries=6,
        seed=seed,
    )

    # Convertiamo i Node in dizionari salvabili in JSON, mantenendo il deposito a indice 0.
    dataset["instances"][instance_id] = [
        {"x": node.x, "y": node.y}
        for node in locations
    ]

    examples = collect_examples(
        locations,
        instance_id=instance_id,
        max_states=max_states,
    )

    dataset["examples"].extend(examples)

    print(f"{instance_id}: {len(examples)} esempi raccolti")

with open("data/examples.json", "w", encoding="utf-8") as file:
    json.dump(dataset, file, indent=2, ensure_ascii=False)

print("Dataset salvato in data/examples.json")

print(f"\nIstanze: {len(dataset['instances'])}")
print(f"Esempi totali: {len(dataset['examples'])}")


# Prendiamo il primo esempio di addestramento, non la prima consegna.
# dataset è ancora in memoria: qui non stiamo rileggendo il file JSON.
example = dataset["examples"][0]
state_example = example["state"]

# Dal dizionario ricostruiamo uno State, per usare attributi come state.unvisited.
# Le liste salvabili in JSON tornano ai tipi usati dal modello: tuple e frozenset.
state = State(
    path= tuple(state_example["path"]),
    unvisited=frozenset(state_example["unvisited"]),
    cost= state_example["cost"]
)

#matrix = distance_matrix(locations)
# L'identificativo collega questo esempio alle coordinate della sua istanza.
# locations, dopo il ciclo, contiene invece l'ultima istanza generata.
istance_id = example["instance_id"]
coordinates = dataset["instances"][istance_id]

# Questa comprensione di lista crea un Node per ogni dizionario in coordinates:
# point è, per esempio, {"x": 3, "y": 4}; Node(x=3, y=4) è l'oggetto corrispondente.
# L'ordine resta identico: gli indici in state.path indicano ancora gli stessi punti.
example_location = [
    Node(x=point["x"], y=point["y"])
    for point in coordinates
]
# matrix[i][j] contiene la distanza tra i punti con indici i e j di questa istanza.
matrix = distance_matrix(example_location)

# Stampiamo le feature dello stato, non ancora una previsione del costo rimanente.
print(extract_features(state, matrix ))
