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


max_states = 100_000

dataset = {
    "instances": {},
    "examples": [],
}

for seed in range(42, 52):
    instance_id = f"istanza_seed_{seed}"

    locations = generate_locations(
        n_deliveries=6,
        seed=seed,
    )

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