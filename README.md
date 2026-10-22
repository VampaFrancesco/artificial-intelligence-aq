# Artificial Intelligence

Repository di lavoro per **Predictive Regulated Search**, applicato al problema
del commesso viaggiatore euclideo (TSP), e per la relativa relazione.

Il problema consiste nel partire da un deposito, visitare ogni consegna una
sola volta e tornare al deposito minimizzando la distanza totale. L'obiettivo
del progetto è confrontare una ricerca di base, una ricerca guidata da un
predittore e una ricerca con predittore e regolatore, usando budget comparabili.

## Contenuto

| Percorso | Contenuto |
| --- | --- |
| [`predictive-regulated-search/`](predictive-regulated-search/) | Codice Python, dati e cartelle per esperimenti, risultati e test. |
| [`tex_files/`](tex_files/) | Sorgenti LaTeX della relazione. |
| [`tex_files/build/homework_regulated_search_Vampa.pdf`](tex_files/build/homework_regulated_search_Vampa.pdf) | PDF della relazione presente nella repository. |
| [`Predictive_Regulated_Search_Homework.pdf`](Predictive_Regulated_Search_Homework.pdf) | Testo dell'homework. |

## Stato del progetto

Sono implementati il caricamento delle coordinate da JSON, il calcolo delle
distanze, la generazione dei successori e due ricerche esatte: DFS esaustiva e
DFS con branch-and-bound. Predittore, regolatore e benchmark sono ancora da
implementare; non è presente una suite di test automatizzati.

Gli algoritmi attuali sono adatti a verifiche su piccole istanze. Una DFS
esaustiva su 100 consegne richiede l'esame di `100!` ordini di visita; la
potatura attuale non rende praticabile in generale un'istanza di questa taglia.
Non sono ancora implementati limiti di tempo o di stati esplorati.

## Da dove iniziare

- Per formato dei dati, configurazione ed esecuzione, leggi la
  [guida del progetto Python](predictive-regulated-search/README.md).
- Per responsabilità dei moduli e rappresentazione degli stati, leggi la
  [guida del codice](predictive-regulated-search/src/README.md).
- Per leggere la relazione, apri il [PDF compilato](tex_files/build/homework_regulated_search_Vampa.pdf).

I comandi Python vanno eseguiti dalla cartella `predictive-regulated-search`,
che è la radice del sottoprogetto, non dall'interno di `src`.
