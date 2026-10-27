# Predictive Regulated Search — TSP euclideo

Esperimenti su sei oppure cento consegne più un deposito. A è una DFS con
branch-and-bound, B ordina i successori con una previsione appresa del costo
rimanente, C cambia periodicamente il candidato dopo stagnazione. Tutti usano
la stessa potatura sicura sul costo già sostenuto e lo stesso budget di estrazioni.

## Usare le posizioni inserite a mano

Il file `data/data.json` contiene il deposito in `depot` e le coordinate delle
consegne in `deliveries`. Per cercare un giro sulla tua mappa:

```sh
python3 -m src.main --input data/data.json --seconds 1
```

Il programma legge i tuoi punti e usa il modello già salvato in `data/model.json`.
Con `--deliveries 100` sceglie invece `data/model_100.json`, se presente.
Il numero di consegne del file viene letto automaticamente: `--deliveries`
sceglie la dimensione di allenamento del modello, non taglia o aggiunge punti.
Se i punti sono diversi per numero o distribuzione dall'allenamento,
l'accuratezza delle previsioni non è garantita. Il programma lo segnala quando
il numero di consegne cambia; mantiene tutte le coordinate fornite.
La modalità `--input` usa il modello senza riallenarlo sulla mappa personale.

Sono confrontati i tre metodi e viene mostrato il miglior percorso trovato.
Il nodo 0 è il deposito; i numeri 1, 2, … seguono l'ordine delle consegne nel file.
Ogni esecuzione salva automaticamente una copia completa in `results/storico/`,
con data, numero di consegne e un nome distinto. La copia contiene coordinate,
parametri del modello, budget e risultati dei tre metodi: modificare in seguito
`data/data.json` non modifica le prove già archiviate. Anche le ripetizioni della
stessa mappa restano separate; le impronte della mappa e del modello permettono
di riconoscerle senza considerarle nuove mappe indipendenti.

`results/mappa_personale.json` rimane la copia dell'ultimo risultato.
`results/confronto_prove.md` raccoglie automaticamente una tabella con costi dei
tre metodi e guadagno percentuale della regolata sulla predittiva nella stessa
prova. Il link di ogni riga apre il relativo salvataggio completo. Non occorre
rinominare file o cambiare la configurazione di avvio. Le prove precedenti
all'introduzione dello storico vengono recuperate soltanto se il loro risultato
completo è ancora disponibile; una prova già sovrascritta va rieseguita.

Per questo comando servono soltanto il file personale e il modello scelto;
i dataset di allenamento non sono richiesti. Non vengono modificati i dataset
o i risultati degli altri esperimenti.

## Come si fa l'esperimento

Il task è una mappa di consegne da risolvere: trovare un ordine di visita che
parta dal deposito, passi da tutte le consegne e ritorni, percorrendo poca strada.
Il modello aiuta la ricerca a scegliere i tentativi; la ricerca produce il giro.

1. Leggi il dataset salvato: le mappe `allenamento_*` forniscono gli esempi.
2. Allena una volta e salva il modello.
3. Usa le mappe `prova_*`, escluse dall'allenamento, come task.
4. Sulla stessa mappa avvia base, predittiva e regolata con lo stesso limite.
5. Confronta distanza dei giri, stati esaminati e risorse impiegate.

Dalla cartella `predictive-regulated-search`:

```sh
python3 -m src.main --deliveries 100 --mode train
python3 -m src.main --deliveries 100 --mode compare
python3 -m src.main --deliveries 100 --seconds 1
```

Il secondo comando confronta 5.000 estrazioni per metodo; il terzo un secondo
di ciclo di ricerca per metodo. `--seconds` sostituisce il budget di stati:
non si interrompe dopo 5.000 stati. Il controllo del tempo avviene fra
iterazioni, con un possibile piccolo superamento nell'ultima iterazione.
I riferimenti offline, la preparazione e il riepilogo finale sono esclusi dal
limite; `elapsed_seconds` include anche il riepilogo finale, mentre
`search_elapsed_seconds` riguarda il ciclo. Le prove temporizzate dipendono
dalla velocità della macchina e possono produrre risultati diversi a ogni avvio.
I loro risultati sono salvati in `results/consegne_100_tempo.json`.

Le prove sulle mappe del dataset sono gli esperimenti dell'assignment. La suite
di test automatici del codice è stata rimossa; il confronto sperimentale rimane.

## Dataset con 100 consegne

Il file `data/consegne_100.json` contiene le coordinate di 15 mappe con 100 consegne
ciascuna, più il deposito: 12 mappe per l'allenamento e 3 per la prova. Le mappe sono
generate con coordinate uniformi in `[0,100]²`; non provengono da consegne reali.
Il dataset contiene anche 40 stati parziali per mappa, per un totale di 600 esempi.
Il campo `splits` indica esplicitamente quali mappe usare per allenare e quali per
verificare: il modello non viene allenato sulle tre mappe di prova.

Usa il programma esistente dalla cartella del sottoprogetto:

```sh
python3 -m src.main --deliveries 100                # prova il modello già incluso
python3 -m src.main --deliveries 100 --mode generate # rigenera solo il dataset
python3 -m src.main --deliveries 100 --mode train    # allena sul dataset salvato
python3 -m src.main --deliveries 100 --mode all      # ripete tutte le fasi
```

Il dataset viene letto da disco anche nella prova: le coordinate delle mappe non
vengono ricreate durante il confronto. Il modello e le sue metriche sono in
`data/model_100.json`; il confronto completo è in `results/consegne_100.json`.
Il budget predefinito è 5.000 estrazioni per metodo, modificabile con `--budgets`.

Per ottenere target praticabili su cento consegne, l'insegnante parte da tre
prime consegne vicine e migliora i completamenti con fino a sei passate di 2-opt.
Ogni esempio conserva il percorso di riferimento, così il target può essere
verificato. I target sono approssimati e dichiarati tali nel dataset.
Per il riferimento finale si usano dodici partenze e fino a venti passate.
Non si calcola il gap dall'ottimo, che qui non conosciamo; il campo resta `null`.

Le modalità delle sezioni successive riproducono invece l'esperimento sulle
mappe piccole: usano dati e modelli distinti, con target certificati.

## Avvio

Esegui dalla cartella `predictive-regulated-search`:

```sh
python3 -m src.main                      # confronto con i dati e il modello inclusi
python3 -m src.main --mode all           # genera, addestra e confronta
python3 -m src.main --mode all --teaching # esperimento didattico separato
```

Per il solo confronto basta la libreria standard. Per addestrare:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Ambiente verificato: Python 3.14.6, scikit-learn 1.9.1. Le modalità `generate`,
`train` e `compare` possono essere avviate separatamente. I percorsi dei dati
sono risolti dalla posizione del progetto, non dal terminale.

## Protocollo

- Seed 42–49: 15.648 stati per l'addestramento.
- Seed 50–51: 3.912 stati esclusi dal fit; hanno contribuito allo sviluppo del regolatore.
- Seed 52–53: nuove mappe valutate con modello e politica già fissati.
- Quattro feature: consegne rimaste, distanza dal deposito, distanza minima e media dalle consegne rimaste.
- Target: costo rimanente ottimo, certificato da un B&B offline con budget 100.000.
- Budget online: 50, 100, 200 e 500 estrazioni; ogni prova riparte da zero.
- Regolatore: dopo 100 estrazioni senza miglioramenti e almeno 100 estrazioni ordinarie dall'ultimo intervento, estrae il candidato con costo parziale minimo.

I riferimenti del confronto sono controllati anche enumerando tutte le permutazioni,
con un limite esplicito di nove consegne residue. Questa valutazione è offline e
non guida A, B o C. Un budget esaurito può restituire un buon giro senza certificarlo.

## Probabilità e bisogno di ricerca

Le alternative sono le prossime consegne dopo il percorso iniziale. La softmax
`exp(-(f(a)-min(f))/T)` normalizzata trasforma i costi previsti in preferenze.
`T` è la distanza media fra tutte le coppie di luoghi (1 se tutte sono coincidenti).
La distribuzione resta fissa per consentire il confronto della massa nel tempo.
Non si campionano azioni: B usa un ordinamento deterministico coerente con le preferenze.

Un'alternativa è irrisolta se il suo sottoalbero contiene almeno uno stato pendente
ancora attivo (`g < miglior costo`). `rho` somma le probabilità di queste alternative,
contandole una sola volta ciascuna. Un primo giro non risolve un intero sottoalbero.
La stessa distribuzione del modello viene usata come misura comune per A, B e C;
A non la usa per scegliere gli stati. Il regolatore usa la stagnazione, non `rho`.
Questa massa non è la probabilità di aver perso l'ottimo e non misura il volume
degli stati inesplorati. Può restare 1 anche dopo aver trovato un giro ottimo.

Le diagnosi offline confrontano la previsione di ogni prima scelta con il suo
miglior completamento esatto, conservando residui, rango e miglioramento rispetto
alla prima scelta predetta. Le tracce mostrano quali rami ricevono calcolo e quando
migliora il giro. Sull'istanza 53, l'azione 6 è ultima per previsione ma conduce
all'ottimo: C la apre al passo 387 e migliora al passo 421; B non la visita entro 500.
Gli errori esatti si conoscono dopo la ricerca e non sono osservazioni online.

## File prodotti

| File | Contenuto |
| --- | --- |
| `data/examples.json` | Coordinate, stati e target certificati. |
| `data/result.json` | Feature, target e identificativi. |
| `data/model.json` | Quattro pesi e intercetta. |
| `data/training_metrics.json` | MAE, separazione dei dati e versioni. |
| `results/search_comparison.json` | Costi, percorsi, gap, tempi, contatori, massa e tracce per A/B/C. |
| `results/choice_diagnostics.json` | Confronto indipendente fra stima e costo esatto per prima scelta. |
| `results/summary.json` | Medie per metodo e budget. |
| `results/experiment_config.json` | Configurazione e parametri usati. |

Con `--teaching`, i dati vanno in `data/didattico` e i risultati in
`results/didattico`. Le dieci mappe hanno quattro consegne; otto sono usate per
addestrare e due per verificare. I budget predefiniti sono 5, 10, 20 e 50.

## Configurazione e limiti

```sh
python3 -m src.main --mode compare --budgets 50 200 500 --patience 100
python3 -m src.main --mode compare --start-path 0 2
```

Le prove riscrivono i risultati della relativa cartella. Il percorso iniziale deve
partire da 0 e non ripetere nodi; costo e consegne residue sono ricostruiti.
Le costanti iniziali di `src/main.py` configurano generazione e modalità predefinita.
Il file storico `data/data.json` e il suo loader restano esempi di input separati;
l'esperimento usa le coordinate di `examples.json` e i seed dichiarati.

La baseline cresce fattorialmente. L'esperimento su sei consegne è piccolo e leggibile. La prova su cento
consegne rimane limitata dal budget e non certifica l'ottimo. Il confronto pareggia le estrazioni, non il
tempo: previsioni, ordinamenti e scansioni aggiungono lavoro. I tempi sono singole
osservazioni comprensive del monitoraggio, senza riferimento offline e softmax;
non costituiscono un benchmark affidabile di velocità. A budget 500 la baseline
raggiunge anch'essa tutti e quattro gli ottimi; il vantaggio di C è rispetto a B.

## Relazione

Dalla cartella `tex_files` della repository:

```sh
tectonic --keep-logs --outdir build homework_regulated_search_Vampa.tex
```

La relazione segue gli otto punti dell'assignment e include il registro AI. Tectonic deve avere disponibili i
pacchetti LaTeX necessari; la prima compilazione può richiedere rete.
