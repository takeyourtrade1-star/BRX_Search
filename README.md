# BRX Search

Microservizio **Search Engine** per il marketplace di carte (Take Your Trade / BRX): sincronizza i dati da **MySQL** a **Meilisearch** (carte singole MTG/OP/PK + prodotti sigillati) ed espone un’API admin per la reindicizzazione.

- **Stack:** Python 3.12, FastAPI, Meilisearch, MySQL  
- **Repo:** [github.com/takeyourtrade1-star/BRX_Search](https://github.com/takeyourtrade1-star/BRX_Search)

---

## Quick start

1. Copia le variabili d’ambiente:
   ```bash
   cp .env.example .env
   ```
   Compila `.env` con: MySQL (host, user, password, database), Meilisearch (URL, master key, index name), `SEARCH_ADMIN_API_KEY` (per reindex). Vedi [.env.example](.env.example).

2. Avvio con Docker (consigliato):
   ```bash
   docker build -t brx-search .
   docker run -d --name search -p 8001:8000 --env-file .env brx-search
   ```
   L’API è su `http://localhost:8001` (porta 8000 nel container).

3. Health check:
   ```bash
   curl http://localhost:8001/
   ```

---

## Reindicizzazione (reindex)

Il **reindex** è il processo che ricostruisce l’indice Meilisearch da MySQL (carte + sealed). Puoi farlo in due modi.

### 1. Script diretto (sul server dove gira il container)

Stesso container che serve l’API, comando unico, output sincrono (conteggi a fine run):

```bash
docker exec search python reindex.py
```

Esempio output: `OK | MTG: 1234 | OP: 56 | PK: 78 | Sealed: 90 | Totale: 1458`

### 2. API HTTP (da remoto)

Da qualsiasi macchina che raggiunge il Search Engine (sostituisci URL e chiave):

```bash
curl -X POST "http://TUO_IP:8001/api/admin/reindex" -H "X-Admin-API-Key: LA_TUA_SEARCH_ADMIN_API_KEY"
```

Risposta **202 Accepted**: il reindex parte in background; i log sono sul server.

- **Sicurezza:** la chiave è quella in `SEARCH_ADMIN_API_KEY` nel `.env`. Dettagli in [docs/ADMIN_API_KEY.md](docs/ADMIN_API_KEY.md).
- **Guida completa** (Docker workflow, PowerShell, troubleshooting): [docs/REINDEX.md](docs/REINDEX.md).

---

## Documentazione

| File | Contenuto |
|------|-----------|
| [docs/REINDEX.md](docs/REINDEX.md) | Reindex: workflow Docker, script diretto, API, riepilogo |
| [docs/ADMIN_API_KEY.md](docs/ADMIN_API_KEY.md) | Sicurezza endpoint reindex (API Key, CORS, deploy) |
| [CHANGELOG_INDEXER.md](CHANGELOG_INDEXER.md) | Modifiche all’indexer (sealed, immagini, lingue, filtri) |

---

## Struttura sintetica

- `app/` – FastAPI app, route admin/health, indexer Meilisearch
- `reindex.py` – Script CLI per reindex senza passare dall’API (incluso nell’immagine Docker)
- `Dockerfile` – Build immagine; `CMD` avvia uvicorn sulla porta 8000

Variabili principali: `MYSQL_*`, `MEILISEARCH_*`, `SEARCH_ADMIN_API_KEY`. Opzionali: `CORS_ORIGINS` (per chiamate dal browser, es. pagina reindex nel frontend), `DEBUG`, `INDEXER_BATCH_SIZE`.
