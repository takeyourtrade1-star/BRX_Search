#!/usr/bin/env python3
"""
Script per recuperare i nomi reali e SVG dei set da CardTrader API.
Popola set_translations per tutti i giochi (Magic, Pokémon, One Piece).
"""

import json
import os
import sys
import time
import requests
from datetime import datetime

# ⚠️ INSERISCI IL TUO TOKEN CARDTRADER QUI
CARDTRADER_API_KEY = "eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJjYXJkdHJhZGVyLXByb2R1Y3Rpb24iLCJzdWIiOiJhcHA6MTk0NzgiLCJhdWQiOiJhcHA6MTk0NzgiLCJleHAiOjQ5MjYwNDQ3NDcsImp0aSI6ImM0MTczN2Y2LTFmZDEtNDJlNC04MTljLTc2YWMwMjAzYjQxZCIsImlhdCI6MTc3MDM3MTE0NywibmFtZSI6Ikp1bGlhblIgQXBwIDIwMjYwMjA2MTA0MjI3In0.LKfwR403r1pCZdl-5yQDZhE3rMFhCzycNH7XiK1ipFxYQnYnXOCibgVGy56IfH_Q06I1aZjWOVwxNeTEsLEgHm6P3dkFS2BVhcJBRdLl8GU3P2bDE6b6Z0n01ZbgIhWQd401lrW5_nR3RiyiUVniT9vsgLqft3y2W9BOAnMvl4_FSRDKOqKqe3xIvNQxYW1JRK9I0TmNxPdaGVRnyGnp_erbqGW2QwWV6XF-DjLs2z75zQ-HkOmt24VvMBKKto_DTkfl0MNzkJlnU3O4qnZKOCixMyyuIkGJH7fAGkFIKh11nUVMmAtFnAjfMjXvjnU0ZGTqL8SD_dmpI6-sXJb-fA"  # Es: "Bearer abc123def456..."
CARDTRADER_API_URL = "https://api.cardtrader.com/v2"

OUTPUT_DIR = 'output/set-data'
SETS_INPUT_FILE = 'output/mtg-sets/mtg_sets_by_cardtrader_id.json'
RATE_LIMIT_DELAY = 0.5  # Secondi tra richieste


def load_sets_from_file():
    """Carica i set da file JSON locale"""
    if not os.path.exists(SETS_INPUT_FILE):
        print(f"✗ File non trovato: {SETS_INPUT_FILE}")
        return {}
    
    with open(SETS_INPUT_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def fetch_set_from_cardtrader(cardtrader_id):
    """
    Recupera le info di un set da CardTrader API.
    Ritorna: {name, code, icon_url, ...}
    """
    if not CARDTRADER_API_KEY or CARDTRADER_API_KEY == "eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJjYXJkdHJhZGVyLXByb2R1Y3Rpb24iLCJzdWIiOiJhcHA6MTk0NzgiLCJhdWQiOiJhcHA6MTk0NzgiLCJleHAiOjQ5MjYwNDQ3NDcsImp0aSI6ImM0MTczN2Y2LTFmZDEtNDJlNC04MTljLTc2YWMwMjAzYjQxZCIsImlhdCI6MTc3MDM3MTE0NywibmFtZSI6Ikp1bGlhblIgQXBwIDIwMjYwMjA2MTA0MjI3In0.LKfwR403r1pCZdl-5yQDZhE3rMFhCzycNH7XiK1ipFxYQnYnXOCibgVGy56IfH_Q06I1aZjWOVwxNeTEsLEgHm6P3dkFS2BVhcJBRdLl8GU3P2bDE6b6Z0n01ZbgIhWQd401lrW5_nR3RiyiUVniT9vsgLqft3y2W9BOAnMvl4_FSRDKOqKqe3xIvNQxYW1JRK9I0TmNxPdaGVRnyGnp_erbqGW2QwWV6XF-DjLs2z75zQ-HkOmt24VvMBKKto_DTkfl0MNzkJlnU3O4qnZKOCixMyyuIkGJH7fAGkFIKh11nUVMmAtFnAjfMjXvjnU0ZGTqL8SD_dmpI6-sXJb-fA":
        print("✗ ERRORE: Token CardTrader non configurato!")
        print("   Modifica CARDTRADER_API_KEY nello script")
        return None
    
    headers = {
        'Authorization': CARDTRADER_API_KEY,
        'Accept': 'application/json'
    }
    
    url = f"{CARDTRADER_API_URL}/sets/{cardtrader_id}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"   ⚠️ Status {response.status_code} per set {cardtrader_id}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Errore fetch: {e}")
        return None


def process_sets(sets_data):
    """
    Processa tutti i set: recupera info da CardTrader e salva.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    total = len(sets_data)
    processed = 0
    successful = 0
    failed = 0
    
    all_set_info = {}
    
    print(f"\n📥 Fetchando {total} set da CardTrader API...")
    print()
    
    for code, set_info in sets_data.items():
        cardtrader_id = set_info.get('cardtrader_id')
        set_id = set_info.get('id')
        
        if not cardtrader_id:
            failed += 1
            continue
        
        # Fetch da API
        api_data = fetch_set_from_cardtrader(cardtrader_id)
        
        if api_data:
            # Mergia dati locali con API
            enriched = {
                'id': set_id,
                'code': code,
                'cardtrader_id': cardtrader_id,
                'local_name': set_info.get('name'),  # Nome locale attuale (spesso errato)
                'api_name': api_data.get('name'),    # Nome corretto da API
                'icon_url': api_data.get('icon_url'),
                'icon_svg': api_data.get('icon_svg'),
                'released_at': api_data.get('released_at'),
                'games': api_data.get('games'),      # Array di giochi supportati
                'api_response': api_data              # Intera risposta per debug
            }
            all_set_info[code] = enriched
            successful += 1
        else:
            failed += 1
        
        processed += 1
        percentage = (processed / total) * 100
        print(f"   {processed}/{total} ({percentage:.1f}%)", end='\r')
        
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)
    
    print(f"\n   ✓ Processati: {successful} set")
    print(f"   ✗ Falliti: {failed} set")
    
    return all_set_info


def save_enriched_sets(all_set_info):
    """Salva i dati arricchiti in JSON"""
    
    # File principale
    output_file = os.path.join(OUTPUT_DIR, 'sets_enriched.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_set_info, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Dati arricchiti salvati: {output_file}")
    
    # Statistiche
    stats = {
        'timestamp': datetime.now().isoformat(),
        'total_sets': len(all_set_info),
        'sets_with_icon_url': sum(1 for s in all_set_info.values() if s.get('icon_url')),
        'sets_with_icon_svg': sum(1 for s in all_set_info.values() if s.get('icon_svg')),
        'sample': {
            code: data for code, data in list(all_set_info.items())[:2]
        } if all_set_info else {}
    }
    
    stats_file = os.path.join(OUTPUT_DIR, 'sets_enriched_stats.json')
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Statistiche salvate: {stats_file}")
    
    return output_file, stats_file


def main():
    print("=" * 70)
    print("FETCH SET DATA DA CARDTRADER API")
    print("=" * 70)
    
    # Verifica token
    if CARDTRADER_API_KEY == "eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJjYXJkdHJhZGVyLXByb2R1Y3Rpb24iLCJzdWIiOiJhcHA6MTk0NzgiLCJhdWQiOiJhcHA6MTk0NzgiLCJleHAiOjQ5MjYwNDQ3NDcsImp0aSI6ImM0MTczN2Y2LTFmZDEtNDJlNC04MTljLTc2YWMwMjAzYjQxZCIsImlhdCI6MTc3MDM3MTE0NywibmFtZSI6Ikp1bGlhblIgQXBwIDIwMjYwMjA2MTA0MjI3In0.LKfwR403r1pCZdl-5yQDZhE3rMFhCzycNH7XiK1ipFxYQnYnXOCibgVGy56IfH_Q06I1aZjWOVwxNeTEsLEgHm6P3dkFS2BVhcJBRdLl8GU3P2bDE6b6Z0n01ZbgIhWQd401lrW5_nR3RiyiUVniT9vsgLqft3y2W9BOAnMvl4_FSRDKOqKqe3xIvNQxYW1JRK9I0TmNxPdaGVRnyGnp_erbqGW2QwWV6XF-DjLs2z75zQ-HkOmt24VvMBKKto_DTkfl0MNzkJlnU3O4qnZKOCixMyyuIkGJH7fAGkFIKh11nUVMmAtFnAjfMjXvjnU0ZGTqL8SD_dmpI6-sXJb-fA":
        print("\n❌ ERRORE: Token CardTrader non configurato!")
        print("\nPer usare questo script:")
        print("1. Vai su https://cardtrader.com/api")
        print("2. Copia il tuo API token")
        print("3. Modifica la linea 14:")
        print('   CARDTRADER_API_KEY = "YOUR_TOKEN_HERE"')
        print("\nEsempio formato token:")
        print('   CARDTRADER_API_KEY = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."')
        sys.exit(1)
    
    try:
        # 1. Carica set locali
        print("\n1. Caricamento set locali...")
        sets_data = load_sets_from_file()
        if not sets_data:
            print("✗ Nessun set trovato!")
            sys.exit(1)
        print(f"✓ Caricati {len(sets_data)} set")
        
        # 2. Fetch da API
        print("\n2. Fetch da CardTrader API...")
        enriched_sets = process_sets(sets_data)
        
        # 3. Salva
        print("\n3. Salvataggio dati...")
        output_file, stats_file = save_enriched_sets(enriched_sets)
        
        # 4. Rapporto
        print()
        print("=" * 70)
        print("✓ COMPLETATO!")
        print("=" * 70)
        print()
        print("File generati:")
        print(f"  - {output_file}")
        print(f"  - {stats_file}")
        print()
        print("Prossimo step:")
        print("  - Popolare set_translations con i nomi arricchiti")
        print("  - Aggiornare sets.name con i nomi corretti da API")
        
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
