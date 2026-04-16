#!/usr/bin/env python3
"""
Script per importare le traduzioni MTG nel database in batch controllati.
Inserisce 100 traduzioni per batch con feedback man mano.
"""

import json
import os
import sys
from datetime import datetime

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("ERRORE: mysql-connector-python non installato.")
    print("Installa con: pip install mysql-connector-python")
    sys.exit(1)


# Credenziali del database
DB_CONFIG = {
    'DB_HOST': os.getenv('MYSQL_HOST', 'srv1502.hstgr.io'),
    'DB_NAME': os.getenv('MYSQL_DATABASE', 'u792485705_mtgfinal'),
    'DB_USER': os.getenv('MYSQL_USER', 'u792485705_final'),
    'DB_PASS': os.getenv('MYSQL_PASSWORD', '7rWolwcD|'),
    'DB_PORT': int(os.getenv('MYSQL_PORT', 3306)),
}

LANGUAGES = ['it', 'fr', 'de', 'es', 'pt']
OUTPUT_DIR = 'output/mtg-cards'
BATCH_SIZE = 100  # Inserisci 100 traduzioni per batch


def get_database_connection():
    """Crea una connessione al database MySQL"""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['DB_HOST'],
            port=DB_CONFIG['DB_PORT'],
            database=DB_CONFIG['DB_NAME'],
            user=DB_CONFIG['DB_USER'],
            password=DB_CONFIG['DB_PASS'],
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            use_unicode=True
        )
        
        if connection.is_connected():
            print(f"✓ Connesso a {DB_CONFIG['DB_NAME']} su {DB_CONFIG['DB_HOST']}")
            return connection
            
    except Error as e:
        print(f"✗ ERRORE connessione: {e}")
        raise


def load_translations(lang):
    """Carica le traduzioni compilate per una lingua."""
    filepath = os.path.join(OUTPUT_DIR, f'mtg_translations_{lang}.json')
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File non trovato: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def import_translations_batch(connection, lang, translations):
    """
    Importa le traduzioni in batch di 100.
    """
    cursor = connection.cursor()
    
    insert_query = """
        INSERT INTO card_translations 
        (game_slug, entity_id, language_code, translated_name)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE translated_name = VALUES(translated_name)
    """
    
    # Filtra solo traduzioni non vuote
    valid_translations = [
        (oracle_id, card_data.get('translated_name', '').strip())
        for oracle_id, card_data in translations.items()
        if card_data.get('translated_name', '').strip()
    ]
    
    print(f"   📍 {lang.upper()}: {len(valid_translations)} traduzioni valide")
    
    total = len(valid_translations)
    inserted = 0
    updated = 0
    errors = 0
    
    # Inserisci in batch
    for batch_idx in range(0, total, BATCH_SIZE):
        batch_end = min(batch_idx + BATCH_SIZE, total)
        batch = valid_translations[batch_idx:batch_end]
        batch_num = (batch_idx // BATCH_SIZE) + 1
        
        try:
            for oracle_id, translated_name in batch:
                cursor.execute(insert_query, (
                    'mtg',              # game_slug
                    oracle_id,          # entity_id
                    lang,               # language_code
                    translated_name     # translated_name
                ))
            
            connection.commit()
            inserted_batch = sum(1 for _ in batch if cursor.lastrowid > 0)
            
            progress = batch_end
            percentage = (progress / total) * 100
            
            print(f"      Batch {batch_num}: {batch_idx}-{batch_end} ({percentage:.1f}%)", end='\r')
            
        except Error as e:
            connection.rollback()
            print(f"\n      ✗ Errore batch {batch_num}: {e}")
            errors += 1
            continue
    
    cursor.close()
    print(f"\n      ✓ Completato: {total} inserite, {errors} errori")
    
    return {
        'inserted': total - errors,
        'errors': errors,
        'total': total
    }


def verify_import(connection, lang):
    """Verifica il numero di traduzioni importate."""
    cursor = connection.cursor()
    
    query = "SELECT COUNT(*) FROM card_translations WHERE game_slug = 'mtg' AND language_code = %s"
    
    try:
        cursor.execute(query, (lang,))
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        cursor.close()


def main():
    """Funzione principale"""
    print("=" * 70)
    print("IMPORTAZIONE TRADUZIONI MTG - BATCH BY BATCH")
    print("=" * 70)
    print()
    
    try:
        # 1. Connetti
        print("1. Connessione al database...")
        connection = get_database_connection()
        print()
        
        # 2. Importa per ogni lingua
        print("2. Importazione traduzioni (batch size: 100)...")
        print()
        
        all_stats = {}
        
        for idx, lang in enumerate(LANGUAGES, 1):
            print(f"   [{idx}/{len(LANGUAGES)}] {lang.upper()}")
            
            # Carica
            try:
                translations = load_translations(lang)
            except FileNotFoundError as e:
                print(f"      ✗ {e}")
                continue
            
            # Importa in batch
            stats = import_translations_batch(connection, lang, translations)
            all_stats[lang] = stats
            
            # Verifica
            db_count = verify_import(connection, lang)
            print(f"      ✓ Verifica DB: {db_count} traduzioni")
            print()
        
        # 3. Chiudi
        if connection.is_connected():
            connection.close()
        
        # 4. Rapporto finale
        print()
        print("=" * 70)
        print("📊 RAPPORTO FINALE")
        print("=" * 70)
        print()
        
        for lang in LANGUAGES:
            if lang in all_stats:
                s = all_stats[lang]
                status = "✓" if s['errors'] == 0 else "⚠"
                print(f"{status} {lang.upper()}: {s['inserted']} traduzioni (errori: {s['errors']})")
        
        total_inserted = sum(s['inserted'] for s in all_stats.values())
        print()
        print(f"TOTALE: {total_inserted} traduzioni importate")
        print()
        print("=" * 70)
        print("[✓] IMPORTAZIONE COMPLETATA!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
