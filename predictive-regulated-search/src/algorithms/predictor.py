import json


# Le quattro feature descrivono il costo ancora necessario, escluso quello passato.
def extract_features(state, matrix):
    # Trasforma uno State nei quattro numeri usati dal predittore.
    # La matrice deve appartenere alla stessa istanza dello stato.
    n_remaining = len(state.unvisited)
    # current_node è l'ultimo indice nel percorso; 0 identifica sempre il deposito.
    distance_to_depot = matrix[state.current_node][0]
    distance_to_remaining = [matrix[state.current_node][node] for node in state.unvisited]
    mean_distance_to_remaining = (
        sum(distance_to_remaining) / n_remaining if n_remaining else 0.0
    )
    distance_to_next_delivery = min(distance_to_remaining, default=0.0)
    return [
        n_remaining,
        distance_to_depot,
        distance_to_next_delivery,
        mean_distance_to_remaining,
    ]


def train_predictor(train_features, train_costs):
    # L'inferenza dai parametri JSON non richiede scikit-learn.
    from sklearn.linear_model import LinearRegression

    model = LinearRegression()
    model.fit(train_features, train_costs)
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
