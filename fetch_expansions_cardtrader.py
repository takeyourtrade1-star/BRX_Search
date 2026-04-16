#!/usr/bin/env python3
"""
Script per recuperare gli expansion data corretti da CardTrader API.
Usa l'endpoint /api/v2/expansions per ottenere nomi reali dei set.
"""

import json
import os
import sys
import requests
from datetime import datetime

# TOKEN CARDTRADER
CARDTRADER_API_KEY = ""
CARDTRADER_API_URL = "https://api.cardtrader.com/api/v2/expansions"

OUTPUT_DIR = 'output/set-data'


def fetch_expansions():
    """
    Recupera tutte le expansion da CardTrader API.
    """
    headers = {
        'Authorization': f'Bearer {CARDTRADER_API_KEY}',
        'Accept': 'application/json'
    }
    
    print(f"📥 Fetching da {CARDTRADER_API_URL}...")
    
    try:
        response = requests.get(CARDTRADER_API_URL, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Fetched {len(data)} expansions")
            return data
        else:
            print(f"✗ Status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Errore: {e}")
        return None


def organize_by_game(expansions):
    """
    Organizza gli expansion per game_id.
    """
    by_game = {}
    
    for exp in expansions:
        game_id = exp.get('game_id')
        if game_id not in by_game:
            by_game[game_id] = []
        by_game[game_id].append(exp)
    
    return by_game


def save_expansions(expansions, by_game):
    """
    Salva i dati degli expansion in JSON.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # File principale (array)
    filepath = os.path.join(OUTPUT_DIR, 'expansions_all.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(expansions, f, ensure_ascii=False, indent=2)
    print(f"✓ Salvati in: {filepath}")
    
    # Per game
    by_game_file = os.path.join(OUTPUT_DIR, 'expansions_by_game.json')
    with open(by_game_file, 'w', encoding='utf-8') as f:
        json.dump(by_game, f, ensure_ascii=False, indent=2)
    print(f"✓ Salvati per game in: {by_game_file}")
    
    # Stats
    stats = {
        'timestamp': datetime.now().isoformat(),
        'total_expansions': len(expansions),
        'games': {game_id: len(exps) for game_id, exps in by_game.items()},
        'sample': expansions[:3]
    }
    
    stats_file = os.path.join(OUTPUT_DIR, 'expansions_stats.json')
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"✓ Statistiche salvate in: {stats_file}")
    
    return filepath


def main():
    print("=" * 70)
    print("FETCH EXPANSIONS DA CARDTRADER API")
    print("=" * 70)
    print()
    
    try:
        # Fetch
        print("1. Connessione a CardTrader API...")
        expansions = fetch_expansions()
        
        if not expansions:
            print("✗ Nessun dato ricevuto!")
            sys.exit(1)
        
        print()
        
        # Organizza
        print("2. Organizzazione dati...")
        by_game = organize_by_game(expansions)
        
        for game_id, exps in by_game.items():
            game_names = {1: "Magic", 2: "Pokémon", 3: "One Piece"}
            game_name = game_names.get(game_id, f"Game {game_id}")
            print(f"   {game_name}: {len(exps)} expansion")
        
        print()
        
        # Salva
        print("3. Salvataggio...")
        save_expansions(expansions, by_game)
        
        print()
        print("=" * 70)
        print("✓ COMPLETATO!")
        print("=" * 70)
        print()
        print("File generati in output/set-data/")
        print("  - expansions_all.json")
        print("  - expansions_by_game.json")
        print("  - expansions_stats.json")
        print()
        print("Prossimo step:")
        print("  - Matchare expansion IDs con cardtrader_id nel DB")
        print("  - Aggiornare sets.name con nomi reali")
        print("  - Popolare set_translations")
        
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
