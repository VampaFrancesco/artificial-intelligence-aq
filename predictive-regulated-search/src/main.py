import json

from .experiments.generate_dataset import (
    collect_examples,
    generate_locations,
)

from .algorithms.predictor import extract_features, train_predictor, load_model_parameters, predict_remaining_cost
from .algorithms.predictive_search import estimated_total_cost
from .algorithms.baseline import BranchAndBound
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

features_list = []
target_costs = [] 
instance_ids = []


for example in dataset["examples"]:
    state_example = example["state"]
    state = State(
        path=tuple(state_example["path"],),
        unvisited=frozenset(state_example["unvisited"]),
        cost=state_example["cost"]
    )
    instance_id=example["instance_id"]
    coordinates= dataset["instances"][instance_id]
    example_location=[
        Node(x=point["x"], y=point["y"])
        for point in coordinates
    ]
    matrix = distance_matrix(example_location)
    features=extract_features(state,matrix)
    target=example["target_cost_to_go"]
    features_list.append(features)
    target_costs.append(target)
    instance_ids.append(instance_id)

"""Crea/modifica un file json che contiene due liste, features dove ogni riga indica rispettivamente
Numero di consegne rimaste,
Distanza dal nodo corrente al deposito,
Distanza alla consegna rimasta più vicina,
Distanza media alle consegne rimaste.
l'altra è target_costs che indica il costo minimo rimanente per completare il giro."""

with open("data/result.json", "w", encoding="utf-8") as file:
    json.dump(
        {"features":features_list, 
         "target_costs":target_costs,
         "instance_ids": instance_ids
         },
        file, 
        indent=2, 
        ensure_ascii=False
        )

test_instance_ids = {"istanza_seed_50", "istanza_seed_51"}

train_features = []
train_costs = []
test_features = []
test_costs = []

for features, target, instance_id in zip(
    features_list, target_costs, instance_ids
):
    if instance_id in test_instance_ids:
        test_features.append(features)
        test_costs.append(target)
    else:
        train_features.append(features)
        train_costs.append(target)

print("Esempi per addestrare:", len(train_features))
print("Esempi per verificare:", len(test_features))

model = train_predictor(train_features, train_costs)

predicted_costs = model.predict(test_features)

total_error = 0
for predicted, actual in zip(predicted_costs, test_costs):
    total_error += abs(predicted - actual)
mean_error = total_error / len(test_costs)

print(mean_error)

constant_prediction = sum(train_costs) / len(train_costs)

constant_total_error = 0

for actual in test_costs:
    constant_total_error += abs(constant_prediction - actual)

constant_mean_error = constant_total_error / len(test_costs)

print(constant_mean_error)


with open("data/model.json", "w", encoding="utf-8") as file:
    json.dump(
        {"weights":model.coef_.tolist(), "intercept":float(model.intercept_)},
        file,
        indent=2,
        ensure_ascii=False
    )

model_data = load_model_parameters("data/model.json")
loaded_prediction = predict_remaining_cost(test_features[0], model_data)
print(loaded_prediction, predicted_costs[0])

state = State(
    path=(0, 2),
    unvisited=frozenset(range(1, len(matrix))) - {2},
    cost=matrix[0][2]
)

ETA = estimated_total_cost(state, matrix, model_data)

print("Costo già percorso:", state.cost)
print("Costo rimanente previsto predittore:", ETA - state.cost)

best_state, is_complete, stats = BranchAndBound(state, matrix, max_states)

if(is_complete == True and best_state != None):
    print("Il costo del Branch&Bound è: ", best_state.cost)
else:
    print("Giro non trovato")

print("Costo rimanente B&B:", best_state.cost - state.cost)