# Ristampe (Meilisearch) — guida operativa

## Architettura

| Concetto | Dettaglio |
|----------|-----------|
| Documento | **1 doc Meilisearch = 1 stampa** (`mtg_{print_id}`, `op_{print_id}`, …) |
| MTG | Campo `oracle_id` (UUID) raggruppa tutte le stampe della stessa faccia |
| OP / PK | Campo `card_id` (string) raggruppa le stampe della stessa carta |
| Frontend | `GET /api/reprints?card_id=mtg_40679` → logica in `lib/reprints-search.ts`, fallback filtri su 400 |
| API key | Solo server: `MEILISEARCH_URL` + `MEILISEARCH_API_KEY` (o `MEILI_*`); **non** esporre master key al browser |
| Indice | `filterableAttributes` deve includere `oracle_id`, `card_id`, `id`, `game_slug`, `category_id` |

## Diagnosi rapida

1. Documento carta contiene `oracle_id` (MTG) o `card_id` (OP/PK)?
2. Impostazioni indice includono quei campi in `filterableAttributes`?
3. Chiave API Meilisearch valida (search + documents)?
4. `game_slug` nel filtro = valore sul documento (es. `mtg`, `op` — **non** mappare `op` → `one-piece` per le ristampe)

---

## Procedura (numerata)

### 1. Verificare impostazioni indice Meilisearch

Sostituisci `MEILI_URL` e `MEILI_MASTER_KEY` (chiave **master** o search con permessi settings).

**PowerShell:**

```powershell
$headers = @{
  Authorization = "Bearer MEILI_MASTER_KEY"
}
Invoke-RestMethod -Uri "https://search.ebartex.com/indexes/cards/settings" -Headers $headers
```

**curl:**

```bash
curl -s -H "Authorization: Bearer MEILI_MASTER_KEY" \
  "https://search.ebartex.com/indexes/cards/settings"
```

Controlla che `filterableAttributes` contenga almeno:  
`id`, `oracle_id`, `card_id`, `game_slug`, `category_id`, `set_name`, `release_date`, `rarity`.

### 2. Verificare un documento campione (es. mtg_40679)

```bash
curl -s -H "Authorization: Bearer MEILI_KEY" \
  "https://search.ebartex.com/indexes/cards/documents/mtg_40679"
```

Deve restituire JSON con `oracle_id`, `game_slug`, `name`, `set_name`.

Test filtro ristampe:

```bash
curl -s -X POST -H "Authorization: Bearer MEILI_KEY" \
  -H "Content-Type: application/json" \
  "https://search.ebartex.com/indexes/cards/search" \
  -d '{"filter":"oracle_id = \"<UUID dal documento>\" AND game_slug = \"mtg\"","limit":5}'
```

- **400** → attributo non filterable → passo 3.
- **0 hit** ma carta esiste → documenti senza `oracle_id` → passo 4 (reindex).

### 3. Applicare solo configurazione indice (senza reindex)

Sul server Search Engine (`Main-app/backend/search_engine`):

```bash
cd Main-app/backend/search_engine
# .env con MEILISEARCH_URL, MEILISEARCH_MASTER_KEY, MEILISEARCH_INDEX_NAME
python configure_index.py
```

**Docker:**

```bash
docker exec <container_search> python configure_index.py
```

**API admin:**

```bash
curl -X POST "http://<SEARCH_HOST>:8001/api/admin/configure-index" \
  -H "X-Admin-API-Key: $SEARCH_ADMIN_API_KEY"
```

### 4. Backfill metadata set (opzionale, icone/date set)

Solo se serve aggiornare `sets` in MySQL prima del reindex:

```bash
cd Main-app/backend/search_engine
python merge_sets_catalog.py   # genera scripts/sets_unified.json se necessario
python backfill_set_metadata.py --dry-run
python backfill_set_metadata.py
```

Variabili: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`.

### 5. Reindex completo (MySQL → Meilisearch)

```bash
cd Main-app/backend/search_engine
python reindex.py
```

**Docker:**

```bash
docker exec <container_search> python reindex.py
```

**API (background):**

```bash
curl -X POST "http://<SEARCH_HOST>:8001/api/admin/reindex" \
  -H "X-Admin-API-Key: $SEARCH_ADMIN_API_KEY"
```

Attendi log: `OK | MTG: … | OP: … | PK: … | Sealed: …`.

### 6. Deploy frontend

Da `Main-app/frontend` (variabili **server** per `/api/reprints`; in produzione preferire queste a `NEXT_PUBLIC_*` per la chiave):

| Variabile | Esempio | Note |
|-----------|---------|------|
| `MEILISEARCH_URL` | `https://search.ebartex.com` | Alias: `MEILI_URL` |
| `MEILISEARCH_API_KEY` | `<chiave search>` | Alias: `MEILI_API_KEY`; permessi search, non master |
| `MEILISEARCH_INDEX` | `cards` | Alias: `MEILI_INDEX` |

Fallback dev (solo se mancano le variabili server): `NEXT_PUBLIC_MEILISEARCH_URL`, `NEXT_PUBLIC_MEILISEARCH_INDEX`.

La pagina prodotto chiama solo `GET /api/reprints` — nessuna richiesta diretta a Meilisearch dal browser per le ristampe.

Build/deploy come da pipeline Ebartex.

### 7. Verifica end-to-end

1. Apri `https://<sito>/products/mtg_40679`
2. DevTools → Network → `GET /api/reprints?card_id=mtg_40679` → 200, `count` > 0
3. Sezione **Ristampe** con miniature altri set

**Locale:**

```bash
cd Main-app/frontend
npm run dev
# http://localhost:3000/products/mtg_40679
```

---

## Riferimenti codice

- Indexer: `app/infrastructure/search/indexer.py` (`configure_meilisearch_index`, `oracle_id` / `card_id` sui documenti)
- Config indice: `configure_index.py`, `POST /api/admin/configure-index`
- Env server Meilisearch (frontend): `lib/meilisearch-server-env.ts`
- API ristampe: `app/api/reprints/route.ts`
- Logica query (single source of truth): `lib/reprints-search.ts`
- UI: `components/feature/product/ProductDetailView.tsx` → solo `/api/reprints`
- Test unitari: `__tests__/lib/reprints-search.test.ts`
