## 1.Activate Virtual Environment

```bash
source .venv/bin/activate
```

## 2.Generate SDK
Remember to give permission with 

```bash
chmod +x scripts/generate.sh
```
(la prima volta farai chmod)

```bash
./scripts/generate.sh
```


## 3 Ruff Lint & Test

```bash
uv run ruff format .
uv run ruff check .

uv run pytest -q # è come uv run pytest -q tests


```

# Workflow

Ogni volta che cambia l’API gli step da fare sono:

aggiorni openapi/openapi.json (anche manualmente)

ricordati di avere docker installato o aver avviato docker desktop

poi fai punto 1 2 e 3.

commit del cambiamento generato + eventuali aggiustamenti.


## Quando si vuole fare una nuova release

1. Usare il comando `uv run pytest` per fare il test
2. (opzionale) Usare il comando `uv run ruff format .` per formattare il codice
3. (opzionale) Usare il comando `uv run ruff check .` per fare il check
4. Usare il comando `uv version --bump patch` per incrementare la versione
5. Merge su main per attivare la pipeline di release.