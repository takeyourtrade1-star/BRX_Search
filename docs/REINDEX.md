# Reindicizzazione Meilisearch – modi semplici e diretti

Come lanciare un full reindex (MySQL → Meilisearch), incluso il flusso **Docker (build in locale → push immagine → deploy)**.

---

## Workflow Docker (build locale → push → deploy)

1. **In locale** (dalla cartella `search_engine`):
   ```bash
   docker build -t brx-search .
   docker run -d --name search -p 8001:8000 --env-file .env brx-search
   ```
   (La porta 8000 è quella interna; 8001 è quella che usi in locale se vuoi.)

2. **Reindex in locale** (stesso container già avviato):
   ```bash
   docker exec search python reindex.py
   ```
   Output: `OK | MTG: ... | OP: ... | ...` (sincrono).

3. **Push e deploy**: fai push dell’immagine sul registry (ECR/Docker Hub), poi su AWS fai pull e run con le variabili d’ambiente di produzione (`.env` o secrets).

4. **Reindex su AWS** (dopo il deploy), due possibilità:
   - **Da fuori** (se la porta è raggiungibile):  
     `curl -X POST "http://IP_PUBBLICO:8001/api/admin/reindex" -H "X-Admin-API-Key: LA_TUA_CHIAVE"`
   - **Sul server AWS** (SSH sulla macchina dove gira il container):  
     `docker exec <nome_container> python reindex.py`  
     Stesso identico comando che in locale: l’immagine contiene già `reindex.py`.

In sintesi: **build e immagine sono gli stessi**; il reindex lo fai con l’API (curl) o con `docker exec ... python reindex.py` sul container in esecuzione.

---

## 1. Script diretto (sul server dove gira il Search Engine)

**Quando usarlo:** sei su AWS (o sulla macchina del Search Engine) e vuoi un comando unico, output chiaro, niente API.

Dalla cartella del progetto Search Engine:

```bash
cd /path/to/search_engine   # es. Main-app/backend/search_engine
python reindex.py
```

- Legge MySQL e Meilisearch dal `.env`.
- Output esempio: `OK | MTG: 1234 | OP: 56 | PK: 78 | Sealed: 90 | Totale: 1458`
- In caso di errore: messaggio su stderr e exit code 1.

---

## 2. API HTTP (da qualsiasi macchina che raggiunge il Search Engine)

**Quando usarlo:** vuoi lanciare il reindex da remoto (PC, CI, altro server) senza SSH sul server Search.

Un solo comando (sostituisci URL e chiave):

```bash
curl -X POST "http://35.152.141.53:8001/api/admin/reindex" -H "X-Admin-API-Key: LA_TUA_SEARCH_ADMIN_API_KEY"
```

Risposta attesa (202):

```json
{"status":"accepted","message":"Reindexing started in background. Check logs for progress."}
```

- Il reindex parte in **background** sul server; i log sono sul processo del Search Engine.
- **403** = chiave sbagliata o mancante. **502 / fetch failed** = la macchina da cui chiami non raggiunge quella porta (firewall, security group, o servizio spento).

Su **Windows (PowerShell)**:

```powershell
Invoke-WebRequest -Uri "http://35.152.141.53:8001/api/admin/reindex" -Method POST -Headers @{"X-Admin-API-Key"="LA_TUA_SEARCH_ADMIN_API_KEY"}
```

---

## Riepilogo

| Metodo        | Dove eseguirlo      | Output / controllo                    |
|---------------|---------------------|---------------------------------------|
| `python reindex.py` | Sul server Search (AWS/locale) | Sincrono, conteggi a fine run        |
| `curl` / API | Da qualsiasi PC     | 202 subito, reindex in background, log sul server |

La chiave `LA_TUA_SEARCH_ADMIN_API_KEY` è il valore che hai messo in `SEARCH_ADMIN_API_KEY` nel `.env` del Search Engine.
