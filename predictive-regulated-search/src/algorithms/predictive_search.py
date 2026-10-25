from .predictor import extract_features, predict_remaining_cost

def estimated_total_cost(state, matrix, model_data):
    if len(state.unvisited) == 0:
        return state.cost + matrix[state.current_node][0]
    else:
        remaining_cost = predict_remaining_cost(extract_features(state, matrix),model_data)

    return state.cost + remaining_cost
        