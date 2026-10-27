# Guida al codice

| Modulo | Responsabilità |
| --- | --- |
| `main.py` | Interfaccia da terminale; generazione, fit, verifica e salvataggio. |
| `models/node.py` | Luogo fisso con coordinate x/y. |
| `models/state.py` | Stato immutabile: percorso, consegne residue e costo accumulato. |
| `models/tsp.py` | Distanze euclidee e successori ordinati per indice. |
| `algorithms/baseline.py` | DFS esaustiva e B&B con budget. |
| `algorithms/predictor.py` | Quattro feature, regressione, parametri JSON e inferenza. |
| `algorithms/predictive_search.py` | Ordinamento predittivo, stagnazione e diversificazione. |
| `algorithms/regulator.py` | Condizione di stagnazione. |
| `algorithms/probability.py` | Softmax, tracciamento per prima scelta e massa irrisolta. |
| `experiments/generate_dataset.py` | Coordinate riproducibili, target esatti da B&B o approssimati da 2-opt per 100 consegne. |
| `experiments/benchmark.py` | Confronto A/B/C, riferimenti esatti sulle mappe piccole o approssimati su 100 consegne. |
| `utils/loader.py` | Loader del formato storico con `depot` e `deliveries`. |

## Stato e ricerca

Il deposito è all'indice 0, `matrix[i][j]` è la distanza fra i luoghi e
`State(path=(0, 3, 2), unvisited=..., cost=...)` conserva il percorso parziale.
`current_node` restituisce l'ultimo indice del percorso. Il ritorno a 0 è aggiunto
quando non restano consegne. I successori hanno costo `g + matrix[u][v]` e sono
nuovi stati, senza modificare il padre.

`BranchAndBound(initial_state, matrix, max_states, observer=None)` e
`predictiveSearch(initial_state, matrix, max_states, model_data, patience=None,
observer=None)` restituiscono `(best_state, is_complete, stats)`.
`best_state=None` significa che non è ancora stato trovato un giro;
`is_complete=True` significa che la pila si è svuotata e l'ottimo è certificato.
La potatura usa solo `g >= best_cost`: una previsione sbagliata cambia l'ordine,
senza eliminare in modo scorretto un ramo. Budget zero è ammesso; budget negativi
sono rifiutati. `patience=None` disabilita il regolatore, una soglia positiva lo abilita.

## Misure

Un'unità del budget è uno stato estratto, compresi terminali e potati.
`states_expanded` conta invece le generazioni dei successori. `model_evaluations`
conta le previsioni usate nell'ordinamento, escludendo terminali e softmax offline.
`diversification_candidates_scanned` conta gli elementi delle scansioni del regolatore.

L'orizzonte contiene stati pendenti, giri valutati e rami potati. La frontiera attiva
contiene solo pendenti con `g < best_cost`; quindi orizzonte e frontiera differiscono.
Gli stati potati non richiedono calcolo; i pendenti all'arresto restano irrisolti.

L'osservatore opzionale non cambia le scelte. Associa ogni discendente alla prima
consegna dopo il percorso iniziale e registra estrazioni, miglioramenti e
interventi. A fine ricerca calcola `rho` sui rami con stati ancora attivi.
Per un percorso iniziale `(0, 2)`, le alternative sono le consegne successive a 2,
non quelle iniziali dal deposito. I riferimenti e i residui esatti sono calcolati
nel benchmark dopo/separatamente dalle decisioni online, senza passarli al regolatore.

La guida operativa completa è nel [README del progetto](../README.md).

Con `--deliveries 100`, `main.py` legge `data/consegne_100.json` e usa le
separazioni `splits.train` e `splits.test` salvate nel dataset. Il modello usa
`data/model_100.json` e i risultati sono raccolti in `results/consegne_100.json`.
La generazione usa `generate_large_dataset` e campiona 40 stati per mappa,
senza enumerare tutti i percorsi. I target e i riferimenti sono dichiarati
approssimati e il gap dall'ottimo resta assente.

`utils/history.py` conserva ogni esecuzione su una mappa personale in
`results/storico/`, con coordinate, parametri del modello e impostazioni.
Mantiene `results/mappa_personale.json` come ultimo risultato e genera
`results/confronto_prove.md` come riepilogo. Le impronte di mappa e modello
separano l'identità del problema dal numero di esecuzioni effettuate.
