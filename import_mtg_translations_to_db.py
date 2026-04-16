#!/usr/bin/env python3
"""
Script per importare le traduzioni MTG compilate nella tabella card_translations.
Legge i file mtg_translations_{lang}.json e popola il database.
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


def get_database_connection():
    """
    Crea una connessione al database MySQL
    """
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
            print(f"[OK] Connesso al database: {DB_CONFIG['DB_NAME']} su {DB_CONFIG['DB_HOST']}:{DB_CONFIG['DB_PORT']}")
            return connection
            
    except Error as e:
        print(f"ERRORE durante la connessione al database: {e}")
        raise


def load_translations(lang):
    """
    Carica le traduzioni compilate per una lingua.
    """
    filepath = os.path.join(OUTPUT_DIR, f'mtg_translations_{lang}.json')
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File non trovato: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"   ✓ Caricate {len(data)} traduzioni per '{lang}'")
    return data


def import_translations_to_db(connection, lang, translations):
    """
    Importa le traduzioni nel database per una lingua specifica.
    """
    cursor = connection.cursor()
    
    # Query per inserire le traduzioni
    insert_query = """
        INSERT INTO card_translations 
        (game_slug, entity_id, language_code, translated_name)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE translated_name = VALUES(translated_name)
    """
    
    inserted = 0
    updated = 0
    skipped = 0
    
    try:
        for oracle_id, card_data in translations.items():
            translated_name = card_data.get('translated_name', '').strip()
            
            # Salta se la traduzione è vuota
            if not translated_name:
                skipped += 1
                continue
            
            try:
                cursor.execute(insert_query, (
                    'mtg',              # game_slug
                    oracle_id,          # entity_id
                    lang,               # language_code
                    translated_name     # translated_name
                ))
                
                if cursor.lastrowid > 0:
                    inserted += 1
                else:
                    updated += 1
                    
            except Error as e:
                print(f"   ⚠️  Errore inserimento '{oracle_id}' ({lang}): {e}")
                continue
        
        connection.commit()
        
        return {
            'inserted': inserted,
            'updated': updated,
            'skipped': skipped,
            'total': inserted + updated + skipped
        }
        
    except Error as e:
        connection.rollback()
        print(f"ERRORE durante l'importazione ({lang}): {e}")
        raise
    finally:
        cursor.close()


def verify_import(connection, lang):
    """
    Verifica il numero di traduzioni importate per una lingua.
    """
    cursor = connection.cursor()
    
    query = """
        SELECT COUNT(*) as count FROM card_translations 
        WHERE game_slug = 'mtg' AND language_code = %s
    """
    
    try:
        cursor.execute(query, (lang,))
        result = cursor.fetchone()
        count = result[0] if result else 0
        return count
    finally:
        cursor.close()


def main():
    """
    Funzione principale
    """
    print("=" * 70)
    print("Importazione Traduzioni MTG nel Database")
    print("=" * 70)
    print()
    
    try:
        # 1. Connetti al database
        print("1. Connessione al database...")
        connection = get_database_connection()
        print()
        
        # 2. Per ogni lingua, carica e importa
        print("2. Importazione traduzioni...")
        print()
        
        all_stats = {}
        
        for lang in LANGUAGES:
            print(f"   📍 Lingua: {lang.upper()}")
            
            # Carica traduzioni
            try:
                translations = load_translations(lang)
            except FileNotFoundError as e:
                print(f"   ❌ {e}")
                continue
            
            # Importa nel database
            stats = import_translations_to_db(connection, lang, translations)
            
            print(f"      Inserted: {stats['inserted']}")
            print(f"      Updated: {stats['updated']}")
            print(f"      Skipped: {stats['skipped']}")
            
            # Verifica
            db_count = verify_import(connection, lang)
            print(f"      DB Count: {db_count}")
            
            all_stats[lang] = stats
            print()
        
        # 3. Chiudi connessione
        if connection.is_connected():
            connection.close()
            print("[OK] Connessione al database chiusa")
        print()
        
        # 4. Rapporto finale
        print("=" * 70)
        print("📊 RAPPORTO IMPORTAZIONE")
        print("=" * 70)
        print()
        
        total_inserted = sum(s['inserted'] for s in all_stats.values())
        total_updated = sum(s['updated'] for s in all_stats.values())
        total_skipped = sum(s['skipped'] for s in all_stats.values())
        
        print(f"Total Inserted: {total_inserted}")
        print(f"Total Updated: {total_updated}")
        print(f"Total Skipped: {total_skipped}")
        print()
        
        for lang in LANGUAGES:
            if lang in all_stats:
                s = all_stats[lang]
                print(f"🌍 {lang.upper()}: {s['inserted']} + {s['updated']} = {s['inserted'] + s['updated']} traduzioni")
        
        print()
        print("=" * 70)
        print("[✓] IMPORTAZIONE COMPLETATA!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
