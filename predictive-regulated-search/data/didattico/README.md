# Dataset didattico

Coordinate inventate e scelte a mano, in unita arbitrarie: non sono dati di
consegne reali. Ogni mappa contiene il deposito all'indice 0 e quattro consegne.
Le forme semplici aiutano a seguire a mano stati, distanze e target.

- `instances.json`: le dieci mappe leggibili e modificabili.
- `examples.json`: 640 stati parziali con costo rimanente ottimo, calcolato
  dal Branch and Bound completo. Il ritorno al deposito e incluso nel target.
- Le otto mappe `train_*` danno 512 esempi per l'allenamento.
- Le due mappe `test_*` danno 128 esempi per la verifica e sono escluse dal fit.

Esempio: in `train_linea`, il percorso `[0, 4]` costa 4. Rimangono le consegne
1, 2 e 3; il miglior completamento e `4 -> 3 -> 2 -> 1 -> 0`, di costo 4.
Il target e quindi 4, mentre il costo totale del giro e 8.

Con `USE_TEACHING_DATA = True`, `main.py` usa questa cartella anche per salvare
il modello durante l'allenamento. I risultati del
confronto vengono salvati in `results/didattico/`.
Con `USE_TEACHING_DATA = False` torna a usare i file dell'esperimento precedente.
`N_DELIVERIES` e `DATASET_SEEDS` configurano solo il generatore casuale.

Questo dataset serve a capire l'allenamento. Con sole quattro consegne molti
budget del confronto consentono di completare la ricerca; non e un benchmark
sufficiente per valutare il regolatore con soglia 100.

Per riprodurre generazione, allenamento e confronto:

```sh
python3 -m src.main --mode all --teaching
```

Esegui dalla radice di `predictive-regulated-search`. I budget predefiniti sono
5, 10, 20 e 50; anche probabilità, massa irrisolta e diagnosi vengono salvate
separatamente in `results/didattico/`. La soglia 100 non interviene a questi budget.

I JSON generati non sono inclusi nel repository: prima dell’uso eseguire
`python3 -m src.main --mode all --teaching`. Solo `instances.json` è conservato.
