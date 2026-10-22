# Guida al codice

Questa cartella contiene il codice Python del TSP euclideo. Per dati e comandi
di avvio, vedi il [README del sottoprogetto](../README.md).

## Moduli e responsabilità

| Modulo | Responsabilità attuale |
| --- | --- |
| `main.py` | Sceglie il JSON, carica i luoghi, costruisce matrice e stato iniziale, esegue DFS e B&B e stampa i risultati. |
| `models/node.py` | Definisce `Node`, un luogo con coordinate `x` e `y`, tramite `@dataclass(frozen=True)`. |
| `models/state.py` | Definisce `State` e la proprietà `current_node`. Attualmente è una dataclass senza `frozen=True`. |
| `models/tsp.py` | Calcola distanze e matrice, genera i successori. Contiene anche i sei luoghi di esempio originali. |
| `utils/loader.py` | `load_location(file_path)` legge un JSON e restituisce una lista di `Node`. |
| `algorithms/baseline.py` | Implementa i generatori di giri DFS e la ricerca branch-and-bound. |
| `algorithms/predictor.py` | Predittore: da implementare. |
| `algorithms/regulator.py` | Regolatore: da implementare. |
| `experiments/benchmark.py` | Confronto sperimentale: da implementare. |

## Luoghi e indici

`Node` rappresenta un luogo fisso, non un nodo dell'albero di ricerca.
Gli stati conservano gli **indici** nella lista `locations`:

```python
locations = [depot, delivery1, delivery2, delivery3]
# indici:       0          1          2          3
```

L'indice identifica il luogo. La posizione di quell'indice in `path` indica
l'ordine della visita. Quindi `path=(0, 3, 2)` significa deposito, consegna 3,
poi consegna 2. L'oggetto attuale si recupera con:

```python
locations[state.current_node]
```

Il deposito deve restare all'indice `0` e l'ordine di `locations` deve rimanere
invariato per tutta la ricerca. `matrix[i][j]` contiene la distanza euclidea
fra `locations[i]` e `locations[j]`.

## Stato e transizioni

Uno stato contiene:

- `path: tuple[int, ...]`: percorso parziale, inizialmente `(0,)`;
- `unvisited: frozenset[int]`: consegne ancora da visitare, senza il deposito;
- `cost: float`: distanza accumulata lungo `path`.

`current_node` è una proprietà calcolata come `path[-1]`: restituisce un indice
e richiede un percorso non vuoto. Tupla e `frozenset` sono immutabili, ma la
classe `State` attuale consente ancora di riassegnare i campi.

`successors(state, matrix)` restituisce una lista con uno stato per ciascuna
consegna ancora da visitare. Per una consegna di indice `node`:

```python
path = state.path + (node,)
unvisited = state.unvisited - {node}
cost = state.cost + matrix[state.current_node][node]
```

Ogni successore è un oggetto nuovo. Lo stato padre e gli altri successori
non vengono modificati. L'ordine di un `frozenset` non va usato come criterio
esplicito per decidere l'ordine di esplorazione.

Quando `unvisited` è vuoto, tutte le consegne sono state visitate. Gli algoritmi
completano il giro aggiungendo `0` al percorso e la distanza di ritorno al costo.

## Algoritmi di base

**`DFS(initial_state, matrix)`** usa una pila LIFO: `pop()` estrae l'ultimo stato
e `extend()` aggiunge i successori. `yield` produce un giro completo alla volta.
È il chiamante, tramite `min(..., key=lambda state: state.cost)`, a consumarli
tutti e selezionare quello meno costoso. Il primo giro prodotto non è
necessariamente ottimo.

**`BranchAndBound(initial_state, matrix)`** restituisce direttamente il miglior
giro completo. Parte da un costo migliore pari a infinito, aggiorna il valore
quando trova un giro migliore e scarta gli stati con costo parziale maggiore
o uguale al miglior costo completo. La potatura è valida con le distanze
euclidee non negative usate qui. Non è ancora presente un limite inferiore
che stimi anche il costo delle consegne rimanenti.

## Flusso di esecuzione e punti da completare

```text
JSON → load_location → locations → distance_matrix
                                → stato iniziale
                                → DFS / BranchAndBound → stampa del giro
```

L'input effettivo di `main.py` viene dal loader: i luoghi di esempio ancora
definiti in `tsp.py` non sostituiscono quelli letti dal file.

Esegui `python3 -m src.main` dalla radice del sottoprogetto per mantenere il
contesto dei pacchetti e degli import relativi. Il blocco dimostrativo di
`tsp.py` richiama attualmente `print_matrix`, che non è definita: non è il
punto d'ingresso da usare per avviare il progetto.

Sono ancora da introdurre validazione dell'input, budget di ricerca,
contatori, salvataggio dei risultati e test. Predittore e regolatore potranno
essere confrontati con la baseline quando saranno disponibili budget e metriche
comuni.
