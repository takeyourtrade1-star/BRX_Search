# Sicurezza endpoint Reindex: API Key al posto del JWT

**Repo:** [BRX_Search](https://github.com/takeyourtrade1-star/BRX_Search)

L’endpoint `POST /api/admin/reindex` non usa più l’autenticazione JWT (Bearer token con ruolo admin/superuser). Ora è protetto da una **API Key** inviata nell’header `X-Admin-API-Key`. Questo documento descrive le modifiche in modo preciso.

---

## 1. Perché il cambio

- **Reindex** è un’operazione amministrativa chiamata da job, script o pipeline (non da un utente loggato nel frontend).
- Usare il JWT richiedeva un token valido (login utente admin o client credentials), con scadenza e gestione refresh.
- Con una **API Key** statica:
  - Lo stesso valore viene configurato nel backend (env) e nel chiamante (CI/CD, cron, script).
  - Niente scadenza token, niente dipendenza dal servizio di auth per questa singola operazione.
  - La chiave resta segreta (SecretStr, mai loggata) e si può ruotare cambiando la variabile d’ambiente.

---

## 2. Modifiche ai file

### 2.1 `app/core/config.py`

**Aggiunto** un nuovo campo obbligatorio nelle `Settings`:

```python
SEARCH_ADMIN_API_KEY: SecretStr = Field(
    ...,
    description="API Key for admin operations (e.g. reindex); send in header X-Admin-API-Key",
)
```

- **Tipo:** `SecretStr` (Pydantic): il valore non viene mai mostrato in repr/log.
- **Obbligatorietà:** `...` → l’applicazione **non avvia** se la variabile d’ambiente `SEARCH_ADMIN_API_KEY` non è impostata (fail-fast).
- **Uso:** confrontato con l’header della richiesta nella dependency `validate_admin_key`.

---

### 2.2 `app/api/dependencies.py`

**Aggiunto** l’import di `Header` da FastAPI:

```python
from fastapi import Depends, Header, HTTPException, status
```

**Aggiunta** la nuova dependency **`validate_admin_key`**:

- **Parametro:** `x_admin_api_key: str | None = Header(None, alias="X-Admin-API-Key")`
  - Legge l’header HTTP **`X-Admin-API-Key`** (alias necessario perché il nome contiene trattini).
  - Se l’header non è presente, il valore è `None`.

- **Logica:**
  1. Recupera il valore atteso: `expected = settings.SEARCH_ADMIN_API_KEY.get_secret_value()`.
  2. Se `expected` è vuoto → **503 Service Unavailable** (configurazione errata).
  3. Se la chiave ricevuta è assente o, dopo strip, diversa da `expected` → **403 Forbidden** con messaggio `"Invalid or missing X-Admin-API-Key"`.
  4. Se corrisponde, la dependency termina senza valore (è solo un controllo di sicurezza).

- **Sicurezza:** il confronto è fatto tra stringhe in memoria; il secret non viene mai loggato né esposto.

---

### 2.3 `app/api/routes/admin.py`

- **Import:** sostituito `get_current_superuser` con `validate_admin_key` (sempre da `app.api.dependencies`).

- **Rotta `POST /reindex`:**
  - **Prima:** `current_user: dict = Depends(get_current_superuser)` → richiedeva `Authorization: Bearer <jwt>` e utente admin/superuser.
  - **Dopo:** `_: None = Depends(validate_admin_key)` → richiede l’header `X-Admin-API-Key` con valore uguale a `SEARCH_ADMIN_API_KEY`. Il parametro `_` indica che non si usa un “utente”, solo il passaggio del controllo.

- **Descrizione OpenAPI:** aggiornata da *"Requires JWT with admin/superuser. Use Authorization: Bearer <access_token>."* a *"Requires header X-Admin-API-Key with the configured admin API key. No JWT."* così in Swagger/ReDoc è chiaro che serve l’header e non il Bearer.

---

### 2.4 `.env.example`

- Aggiunta la riga:
  ```bash
  # Admin API Key (for reindex etc.; send in header X-Admin-API-Key)
  SEARCH_ADMIN_API_KEY=
  ```
- Serve da promemoria per chi fa il deploy: la variabile **deve** essere impostata nel `.env` (o nelle env del container/ambiente), con un valore segreto e robusto.

---

## 3. Come chiamare l’endpoint

**Esempio con curl:**

```bash
curl -X POST "https://your-search-engine/api/admin/reindex" \
  -H "X-Admin-API-Key: il-valore-configurato-in-SEARCH_ADMIN_API_KEY"
```

**Risposta attesa (202 Accepted):**

```json
{
  "status": "accepted",
  "message": "Reindexing started in background. Check logs for progress."
}
```

**Errori:**

- **403 Forbidden:** header assente o valore di `X-Admin-API-Key` diverso da `SEARCH_ADMIN_API_KEY`.
- **503 Service Unavailable:** `SEARCH_ADMIN_API_KEY` non configurata (stringa vuota).

---

## 4. Riepilogo sicurezza

| Aspetto              | Dettaglio                                                                 |
|----------------------|---------------------------------------------------------------------------|
| Dove si invia la key | Header HTTP `X-Admin-API-Key` (non in query o in body).                  |
| Dove si configura    | Variabile d’ambiente `SEARCH_ADMIN_API_KEY` (es. in `.env` o in AWS/SSM). |
| Tipo in config       | `SecretStr` (Pydantic): non esposto in log o repr.                        |
| Confronto            | Stringa ricevuta vs `get_secret_value()`; nessun timing leak curato in questo step. |
| Rotazione            | Cambiare `SEARCH_ADMIN_API_KEY` e aggiornare i chiamanti (script/CI).     |

---

## 5. Checklist deploy

1. Impostare `SEARCH_ADMIN_API_KEY` nell’ambiente (es. `.env` o secrets del container).
2. Usare un valore lungo e casuale (es. generato con `openssl rand -hex 32`).
3. Configurare lo stesso valore nello script/job che chiama `POST /api/admin/reindex` (header `X-Admin-API-Key`).
4. Non committare mai il file `.env` (è già in `.gitignore`).
