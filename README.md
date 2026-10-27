# Predictive Regulated Search — TSP euclideo

Progetto di Artificial Intelligence: un veicolo parte dal deposito, visita tutte
le consegne e torna al deposito minimizzando la distanza. Confronta:

- **A**: DFS con branch-and-bound;
- **B**: ricerca ordinata da un modello lineare del costo rimanente;
- **C**: ricerca predittiva con diversificazione dopo stagnazione.

Il programma comprende generazione dei target, addestramento, confronto a budget
uguali, probabilità sulle prime scelte, massa irrisolta e analisi dell'errore.
Sulle mappe piccole il riferimento viene verificato anche con un'enumerazione indipendente.

## Usare la propria mappa

Inserisci deposito e consegne in `predictive-regulated-search/data/data.json`.
Dalla cartella del sottoprogetto:

```sh
python3 -m src.main --input data/data.json --seconds 1
```

Questo comando usa il modello già salvato e cerca un giro sui punti inseriti.
Non richiede il dataset da 100 consegne. Il modello predefinito è allenato su
mappe da sei consegne: su mappe di dimensione o distribuzione diversa le
previsioni vanno considerate sperimentali.
Ogni prova personale viene conservata con la sua mappa in
`results/storico/`; `results/confronto_prove.md` mostra il confronto fra le
esecuzioni. La configurazione di avvio resta la stessa.

## Dataset con 100 consegne

Il dataset generato in `data/consegne_100.json` comprende
15 mappe, ognuna con deposito e 100 consegne. Il file distingue 12 mappe
di allenamento da 3 mappe di prova e include 600 stati parziali con i loro target.
I nomi sono `allenamento_01`, `allenamento_02`, … e `prova_01`, `prova_02`, `prova_03`.

Se dataset e modello sono presenti, dalla cartella `predictive-regulated-search`:

```sh
python3 -m src.main --deliveries 100
```

Il modello allenato su queste mappe viene salvato in `data/model_100.json`.
I task sono le tre mappe di prova già contenute nel dataset. Per allenare dal
file salvato e poi confrontare anche con lo stesso limite temporale:

```sh
python3 -m src.main --deliveries 100 --mode train
python3 -m src.main --deliveries 100 --seconds 1
```

Per rigenerare il dataset, allenare e confrontare da capo:

```sh
python3 -m src.main --deliveries 100 --mode all
```

Su 100 consegne i target sono giri approssimati migliorati con 2-opt, non ottimi
certificati. I risultati vanno in `results/consegne_100.json`. Gli esperimenti
esatti sulle mappe piccole restano disponibili con i comandi sotto.

## Riprodurre l'esperimento

Dalla radice della repository:

```sh
cd predictive-regulated-search
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m src.main --mode all
```

Ambiente verificato: Python 3.14.6 e scikit-learn 1.9.1. Con dataset e modelli
inclusi, `python3 -m src.main` ripete soltanto il confronto e non richiede
scikit-learn. Non occorrono connessioni esterne per questo confronto.

## Materiale

| Percorso | Contenuto |
| --- | --- |
| [Guida Python](predictive-regulated-search/README.md) | Comandi, configurazione e risultati. |
| [Guida al codice](predictive-regulated-search/src/README.md) | Moduli, stati e definizioni delle misure. |
| [Relazione](tex_files/build/homework_regulated_search_Vampa.pdf) | Progetto, esperimenti, limiti e registro AI. |
| [Sorgenti LaTeX](tex_files/) | Relazione modificabile e bibliografia. |
| [Consegna originale](Predictive_Regulated_Search_Homework.pdf) | Requisiti dell'homework. |

## Risultato principale

Sull'istanza 53, con 500 estrazioni, B ha un gap dell'1,55%; C trova l'ottimo.
Il ramo classificato ultimo dal modello non riceve estrazioni in B, mentre C
lo apre al passo 387 e trova il giro ottimo al passo 421. La regolazione non
migliora ogni istanza: i risultati riguardano quattro piccole mappe, due delle
quali usate nello sviluppo della politica, e non dimostrano un vantaggio generale.
Le probabilità indicano preferenze di esplorazione, non confidenze sull'ottimalità.
