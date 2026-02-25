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