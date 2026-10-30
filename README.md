# Predictive Regulated Search. TSP euclideo

Progetto di Artificial Intelligence: cercare un giro dal deposito che visiti
ogni consegna e torni al punto di partenza. Confronta tre metodi:

- **A**: ricerca in profondità con branch-and-bound;
- **B**: ricerca guidata da una previsione appresa del costo rimanente;
- **C**: ricerca predittiva con regolazione dopo stagnazione.

## Eseguire l'esperimento della relazione

```sh
cd predictive-regulated-search
python3 -m src.main --mode experiment
```

Usa i dataset e i modelli inclusi, senza riallenamento e senza dipendenze esterne
alla libreria standard Python. Confronta dieci mappe da 100 consegne, con budget
nominali di 1 e 3 secondi e tre ripetizioni: circa sei minuti di sola ricerca.
Riproduce anche il caso piccolo con ottimo verificato tramite enumerazione.

Ogni esecuzione salva coordinate, parametri, percorsi, tempi e riepilogo in una
nuova cartella `results/esperimenti/`. **Tutte le cartelle dei risultati sono
escluse da Git** e vengono generate sul computer di chi esegue il progetto.
Le due esecuzioni descritte nella relazione sono conservate localmente.

Nelle prove riportate, la regolata migliora la predittiva su 6 mappe su 10 a
1 secondo e su 7 a 3 secondi. La riduzione media della distanza è rispettivamente
2,04% e 3,07%. Sono risultati su queste mappe, non una garanzia generale.

## Usare le proprie consegne

Modifica `predictive-regulated-search/data/data.json`, quindi dalla cartella del
sottoprogetto esegui:

```sh
python3 -m src.main --deliveries 100 --input data/data.json --seconds 1
```

Questo comando usa il modello allenato su mappe da 100 consegne. Senza
`--deliveries 100` viene usato il modello piccolo da sei consegne.

## Allenare e rigenerare i dati

Per il solo allenamento serve scikit-learn:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m src.main --deliveries 100 --mode train
```

Il dataset grande contiene 12 mappe di allenamento e 3 di verifica, con
480 esempi di allenamento e 120 di verifica. I target grandi sono completamenti
euristici, non ottimi certificati. Il dataset piccolo serve all'allenamento del
modello da sei consegne e alla verifica della separazione dei dati.

`--mode all` rigenera dati, modello e confronto della dimensione scelta.
Il materiale didattico si genera con `python3 -m src.main --mode all --teaching`.
Ambiente verificato: Python 3.14.6 e scikit-learn 1.9.1.

## Materiale

| Percorso | Contenuto |
| --- | --- |
| [Guida Python](predictive-regulated-search/README.md) | Comandi e configurazione. |
| [Guida al codice](predictive-regulated-search/src/README.md) | Moduli e misure. |
| [Relazione](tex_files/build/homework_regulated_search_Vampa.pdf) | Progetto, esperimenti e registro AI. |
| [Sorgenti LaTeX](tex_files/) | Relazione modificabile. |
| [Consegna originale](Predictive_Regulated_Search_Homework.pdf) | Requisiti dell'homework. |

Dati di input, modelli, sorgenti e PDF finale sono versionati. Output degli
esperimenti, cache, ambienti Python e file intermedi LaTeX restano locali.
