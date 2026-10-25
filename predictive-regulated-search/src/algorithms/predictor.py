import json

from sklearn.linear_model import LinearRegression

#funzione che descrive lo stato di un nodo del TSP, ritorna 3 numeri ovvero i nodi rimanenti, la distanza dal deposito e l a distanza alla prossima consegna
def extract_features(state, matrix):
    # Trasforma uno State in numeri che useremo come input del futuro predittore.
    # La matrice deve appartenere alla stessa istanza dello stato.
    n_remaining = len(state.unvisited)
    # current_node è l'ultimo indice nel percorso; 0 identifica sempre il deposito.
    distance_to_depot = matrix[state.current_node][0]
    # Ordine delle feature: [numero di consegne rimaste, distanza dal deposito].
    distance_to_remaining = [
        matrix[state.current_node][y]
        for y in state.unvisited
    ]

    
    mean_distance_to_remaining = sum(distance_to_remaining)/ n_remaining if n_remaining > 0 else 0

    
    distance_to_next_delivery = min(distance_to_remaining, default=0)
    return [
            n_remaining, 
            distance_to_depot,
            distance_to_next_delivery, 
            mean_distance_to_remaining
            ]

def train_predictor(train_features, train_costs):
    model = LinearRegression()
    model.fit(train_features,train_costs)
    return model

def load_model_parameters(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        model_data = json.load(file)
    return model_data

def predict_remaining_cost(features, model_data):
    prediction = model_data["intercept"]
    for feature, weight in zip(features, model_data["weights"]):
        prediction += feature * weight
    return prediction