# Modifiche all'indexer Meilisearch (BRX_Search)

**Repo:** [https://github.com/takeyourtrade1-star/BRX_Search](https://github.com/takeyourtrade1-star/BRX_Search)  
**File:** `app/infrastructure/search/indexer.py`

---

## Riepilogo

- **Prodotti sigillati (Sealed):** nuova funzione `_index_sealed_products` che indicizza box, bustine e mazzi dalla tabella `sealed_products` (esclusa categoria 1 = carte singole).
- **Immagini:** tutte le immagini vengono **recuperate dal DB** (nessun path costruito in codice): `image_path` per MTG/OP/sealed, `image_url` per PK.
- **Lingue:** la gestione multilingua (traduzioni + `keywords_localized`) resta **solo per Magic (MTG)**; OP e PK indicizzano solo il nome dal DB.
- **Filtri:** aggiunti `category_id` e `game_slug` nei filterable attributes per la barra di ricerca (es. “solo Box One Piece”, “solo Carte Singole”).

---

## 1. Carte singole: MTG, OP, PK

### Immagini (dal DB)
- **MTG:** `cp.image_path` dalla tabella `cards_prints`.
- **OP:** `op.image_path` dalla tabella `op_prints`.
- **PK:** `pp.image_url` (alias `image_path`) dalla tabella `pk_prints`.

Nessun path viene inventato: si usa solo il valore salvato in database.

### Categoria
- Ogni documento ha: `"category_id": 1`, `"category_name": "Carta Singola"`.

### Gestione lingue (solo MTG)
- **MTG:** come prima: caricamento traduzioni da `card_translations`, `_build_keywords_localized`, documento con `keywords_localized` per la ricerca multilingua.
- **OP e PK:** nessun fetch da `card_translations`; documento senza `keywords_localized` (solo `name`, `set_name`, `game_slug`, `category_id`, `category_name`, `image`).

---

## 2. Nuova funzione: `_index_sealed_products`

- **Tabella:** `sealed_products` con JOIN su `sets` e `games` per `set_name` e `game_slug`.
- **Filtro:** `WHERE sp.category_id != 1` (esclusione carte singole).
- **Nome:** `COALESCE(sp.name_en, sp.name_it, '')`.
- **Immagini:** da DB → `sp.image_path` (nessun path costruito).
- **Documento:** `id` = `sealed_{product_id}`, `name`, `set_name`, `game_slug`, `category_id`, `image`.
- **Batching:** stessa logica a batch (default 5000) delle altre funzioni.

---

## 3. Configurazione Meilisearch: `_configure_meilisearch_index`

- **filterableAttributes:** `["game_slug", "category_id", "set_name"]`  
  → filtri in barra di ricerca (gioco, categoria, set).
- **searchableAttributes:** `["name", "keywords_localized", "set_name"]`.

---

## 4. `run_indexer`

- Aggiunto `result["sealed"]` e chiamata a `_index_sealed_products`.
- Totale: `result["total"] = result["mtg"] + result["op"] + result["pk"] + result["sealed"]`.
- Log con conteggi: mtg, op, pk, sealed, total.

---

## Come eseguire il reindex

Dopo il deploy, chiamare l’endpoint admin che invoca `run_indexer()` (es. `POST /admin/reindex`) per sincronizzare MySQL → Meilisearch.
