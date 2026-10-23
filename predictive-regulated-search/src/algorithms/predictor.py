
def extract_features(state, matrix):
    # Trasforma uno State in numeri che useremo come input del futuro predittore.
    # La matrice deve appartenere alla stessa istanza dello stato.
    n_remaining = len(state.unvisited)
    # current_node è l'ultimo indice nel percorso; 0 identifica sempre il deposito.
    distance_to_depot = matrix[state.current_node][0]
    # Ordine delle feature: [numero di consegne rimaste, distanza dal deposito].
    return [n_remaining, distance_to_depot]
