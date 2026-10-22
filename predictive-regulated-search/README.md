# Predictive Regulated Search — TSP euclideo

Implementazione didattica del giro di consegne: partenza dal deposito, visita
di tutte le consegne e ritorno al deposito, minimizzando la distanza euclidea.

Al momento sono disponibili il loader JSON, la matrice delle distanze, gli
stati di ricerca, la generazione dei successori, DFS esaustiva e branch-and-bound.
Predittore, regolatore e benchmark sono ancora file vuoti.

## Struttura

```text
predictive-regulated-search/
├── src/
│   ├── main.py              # Caricamento, esecuzione e stampa dei risultati
│   ├── models/              # Luoghi, stati, distanze e successori
│   ├── utils/loader.py      # Lettura delle coordinate da JSON
│   ├── algorithms/         # DFS e B&B; predittore e regolatore da implementare
│   └── experiments/        # Benchmark da implementare
├── data/data.json           # Istanza di input predefinita
├── results/                # Destinazione prevista per i risultati
├── tests/                  # Test ancora da scrivere
└── requirements.txt         # Attualmente vuoto
```

Per i dettagli sui singoli moduli, vedi [`src/README.md`](src/README.md).

## Ambiente

Il codice usa solo la libreria standard di Python. Le annotazioni usate
richiedono Python 3.9 o successivo; lo sviluppo corrente usa Python 3.14.
Non ci sono dipendenze esterne da installare.

Esegui i comandi dalla radice del sottoprogetto:

```sh
cd predictive-regulated-search
```

Se usi l'ambiente virtuale attualmente presente in `src/.venv`, attivalo con:

```sh
source src/.venv/bin/activate
```

## Formato JSON

Il deposito è esplicito e separato dalle consegne. Il loader restituisce una
lista di oggetti `Node`: deposito all'indice `0`, poi le consegne nell'ordine
del file. Per esempio:

```json
{
  "depot": {"x": 0, "y": 0},
  "deliveries": [
    {"x": 3, "y": 4},
    {"x": 6, "y": 1}
  ]
}
```

Questo file descrive due consegne più il deposito. Le coordinate devono essere
numeri JSON, con il punto per i decimali. Il loader assume che campi e tipi
siano corretti: non implementa ancora validazione esplicita. CSV e TXT non
sono ancora supportati.

## Esecuzione

**Prima di avviare la ricerca, controlla la dimensione del file:** l'istanza
attualmente in `data/data.json` contiene 100 consegne e non è adatta alla DFS
esaustiva. Per verificare gli algoritmi, usa inizialmente 6–8 consegne.

Il comando che carica il file predefinito è:

```sh
python3 -m src.main
```

Per scegliere un altro JSON, passa il percorso con la variabile d'ambiente
`file_path`. Per esempio, dopo aver creato un'istanza piccola in `data/small.json`:

```sh
file_path=data/small.json python3 -m src.main
```

Il nome `file_path` è sensibile a maiuscole e minuscole. I percorsi relativi
sono risolti dalla cartella corrente. Un file `.env` non viene caricato
automaticamente: `main.py` legge solo le variabili già presenti nell'ambiente.

## Risultati e garanzie

`main.py` mostra lo stato iniziale e le prime mosse, poi esegue in sequenza:

1. DFS, consumando tutti i giri generati e scegliendo il meno costoso con `min`.
2. Branch-and-bound, conservando il miglior giro e potando i rami già troppo costosi.

Entrambi includono il ritorno al deposito nel costo finale. Se la ricerca
termina, restituiscono un giro ottimo per l'istanza. Possono esistere più giri
ottimi, incluso lo stesso giro percorso al contrario.

La visualizzazione arrotonda i costi a tre decimali; i calcoli mantengono la
precisione dei numeri `float`. I risultati sono stampati nel terminale: non
vengono ancora salvati automaticamente in `results/`.

## Limiti attuali

- La DFS esamina `n!` ordini per `n` consegne. Con 100 consegne è impraticabile.
- Il B&B usa come limite inferiore il solo costo parziale. Non è un risolutore
  scalabile per istanze generiche da 100 consegne.
- Se la DFS non termina, `main.py` non raggiunge la chiamata al B&B.
- Non ci sono budget di ricerca, contatori degli stati o test automatizzati.
- Durante la ricerca non vengono stampati aggiornamenti di avanzamento;
  `Ctrl+C` interrompe l'esecuzione e produce un `KeyboardInterrupt`.

I prossimi passi previsti sono introdurre budget e misure confrontabili,
quindi implementare predittore, regolatore e benchmark. Un risultato ottenuto
interrompendo una ricerca richiederà di distinguere il miglior giro trovato
da un ottimo dimostrato.
