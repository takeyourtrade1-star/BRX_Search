#!/usr/bin/env python3
"""
Script per estrarre tutti i set MTG dal database e salvarli in JSON locale.
Preparazione per il fetch dei nomi reali da Scryfall API.
"""

import json
import os
import sys

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("ERRORE: mysql-connector-python non installato.")
    sys.exit(1)


# CREDENZIALI
DB_CONFIG = {
    'DB_HOST': 'srv1502.hstgr.io',
    'DB_NAME': 'u792485705_mtgfinal',
    'DB_USER': 'u792485705_final',
    'DB_PASS': '7rWolwcD|',
    'DB_PORT': 3306,
}

OUTPUT_DIR = 'output/mtg-sets'


def get_connection():
    """Connessione al database"""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['DB_HOST'],
            port=DB_CONFIG['DB_PORT'],
            database=DB_CONFIG['DB_NAME'],
            user=DB_CONFIG['DB_USER'],
            password=DB_CONFIG['DB_PASS'],
            charset='utf8mb4',
            use_unicode=True
        )
        print(f"✓ Connesso a {DB_CONFIG['DB_NAME']}")
        return conn
    except Error as e:
        print(f"✗ ERRORE: {e}")
        raise


def extract_sets(connection):
    """Estrae tutti i set dal database"""
    cursor = connection.cursor(dictionary=True)
    
    query = """
        SELECT 
            id,
            cardtrader_id,
            code,
            name,
            release_date,
            game_id
        FROM sets
        ORDER BY release_date DESC
    """
    
    try:
        cursor.execute(query)
        sets_data = cursor.fetchall()
        cursor.close()
        
        print(f"✓ Estratti {len(sets_data)} set")
        return sets_data
        
    except Error as e:
        print(f"✗ ERRORE: {e}")
        raise


def save_sets_locally(sets_data):
    """Salva i set in JSON locale"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Converti date in stringhe
    for s in sets_data:
        if s['release_date']:
            s['release_date'] = s['release_date'].isoformat()
    
    # Salva file principale
    filepath = os.path.join(OUTPUT_DIR, 'mtg_sets_raw.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sets_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Salvati in: {filepath}")
    
    # Salva anche in formato dict {cardtrader_id: set_data} per fetch da API
    sets_by_ct_id = {str(s['cardtrader_id']): s for s in sets_data if s['cardtrader_id']}
    
    filepath_by_ct_id = os.path.join(OUTPUT_DIR, 'mtg_sets_by_cardtrader_id.json')
    with open(filepath_by_ct_id, 'w', encoding='utf-8') as f:
        json.dump(sets_by_ct_id, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Salvati per cardtrader_id in: {filepath_by_ct_id}")
    
    # Statistiche
    stats = {
        'total_sets': len(sets_data),
        'sets_with_code': sum(1 for s in sets_data if s['code']),
        'sets_with_release_date': sum(1 for s in sets_data if s['release_date']),
        'sets_with_cardtrader_id': sum(1 for s in sets_data if s['cardtrader_id'])
    }
    
    stats_filepath = os.path.join(OUTPUT_DIR, 'mtg_sets_stats.json')
    with open(stats_filepath, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Statistiche salvate in: {stats_filepath}")
    print()
    print("📊 STATISTICHE:")
    print(f"   Total sets: {stats['total_sets']}")
    print(f"   With code: {stats['sets_with_code']}")
    print(f"   With release_date: {stats['sets_with_release_date']}")
    print(f"   With cardtrader_id: {stats['sets_with_cardtrader_id']}")
    
    return filepath, filepath_by_ct_id


def main():
    print("=" * 70)
    print("ESTRAZIONE SET MTG DAL DATABASE")
    print("=" * 70)
    print()
    
    try:
        # Connetti
        print("1. Connessione al database...")
        connection = get_connection()
        print()
        
        # Estrai
        print("2. Estrazione set...")
        sets_data = extract_sets(connection)
        connection.close()
        print()
        
        # Salva
        print("3. Salvataggio locale...")
        filepath, filepath_by_ct_id = save_sets_locally(sets_data)
        print()
        
        print("=" * 70)
        print("✓ COMPLETATO!")
        print("=" * 70)
        print()
        print("File generati:")
        print(f"  - {filepath}")
        print(f"  - {filepath_by_ct_id}")
        print()
        print("Prossimo step:")
        print("  - Fetch Scryfall API per nomi reali e SVG")
        print("  - Creare tabella set_translations")
        print("  - Popolare con traduzioni dei nomi")
        
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
