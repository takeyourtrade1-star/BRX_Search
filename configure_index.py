#!/usr/bin/env python3
"""
Applica solo le impostazioni Meilisearch (filterable / searchable / sortable)
senza reindicizzare i documenti.

Uso (dalla cartella search_engine, con .env):
  python configure_index.py

In Docker:
  docker exec <container> python configure_index.py
"""
import sys

sys.path.insert(0, ".")


def main() -> None:
    from app.infrastructure.search.indexer import configure_meilisearch_index

    print("Configurazione indice Meilisearch...")
    configure_meilisearch_index()
    print("OK — filterableAttributes include id, oracle_id, card_id, game_slug, category_id, ...")


if __name__ == "__main__":
    main()
