#!/usr/bin/env python3
"""
Reindicizzazione diretta: esegue il full reindex da MySQL a Meilisearch
senza passare dall'API HTTP. Da usare sul server (AWS o locale).

Uso (dalla cartella search_engine):
  python reindex.py

Richiede .env con MySQL e Meilisearch configurati.
"""
import sys

# Assicura che il package app sia importabile dalla root del progetto
sys.path.insert(0, ".")


def main() -> None:
    from app.infrastructure.search.indexer import run_indexer

    print("Avvio reindicizzazione...")
    result = run_indexer()
    if result.get("error"):
        print("ERRORE:", result["error"], file=sys.stderr)
        sys.exit(1)
    print(
        f"OK | MTG: {result['mtg']} | OP: {result['op']} | PK: {result['pk']} | Sealed: {result['sealed']} | Totale: {result['total']}"
    )


if __name__ == "__main__":
    main()
