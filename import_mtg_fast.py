#!/usr/bin/env python3
"""
Script VELOCE per importare traduzioni MTG in bulk.
Usa INSERT multipli (1000 righe per query) invece di uno per uno.
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


# CREDENZIALI CORRETTE
DB_CONFIG = {
    'DB_HOST': 'srv1502.hstgr.io',
    'DB_NAME': 'u792485705_mtgfinal',
    'DB_USER': 'u792485705_final',
    'DB_PASS': '7rWolwcD|',
    'DB_PORT': 3306,
}

OUTPUT_DIR = 'output/mtg-cards'
BULK_SIZE = 1000  # Inserisci 1000 record per query


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


def load_translations(lang):
    """Carica traduzioni JSON"""
    filepath = os.path.join(OUTPUT_DIR, f'mtg_translations_{lang}.json')
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File non trovato: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def import_language_bulk(connection, lang):
    """Importa una lingua con INSERT bulk"""
    
    print(f"\n📍 Caricamento {lang.upper()}...")
    
    # Carica traduzioni
    translations = load_translations(lang)
    
    # Filtra solo traduzioni non vuote
    valid_data = [
        (oracle_id, card_data.get('translated_name', '').strip())
        for oracle_id, card_data in translations.items()
        if card_data.get('translated_name', '').strip()
    ]
    
    print(f"   → {len(valid_data)} traduzioni da inserire")
    
    cursor = connection.cursor()
    total = len(valid_data)
    inserted = 0
    
    # Inserisci in bulk di 1000
    for batch_start in range(0, total, BULK_SIZE):
        batch_end = min(batch_start + BULK_SIZE, total)
        batch = valid_data[batch_start:batch_end]
        
        # Costruisci query con VALUES multipli
        values_list = []
        for oracle_id, translated_name in batch:
            # Escape dei caratteri speciali
            translated_name = translated_name.replace("'", "\\'")
            values_list.append(f"('mtg', '{oracle_id}', '{lang}', '{translated_name}')")
        
        query = f"""
            INSERT INTO card_translations 
            (game_slug, entity_id, language_code, translated_name)
            VALUES {','.join(values_list)}
            ON DUPLICATE KEY UPDATE translated_name = VALUES(translated_name)
        """
        
        try:
            cursor.execute(query)
            connection.commit()
            inserted += len(batch)
            percentage = (inserted / total) * 100
            
            # Feedback ogni batch
            print(f"   ✓ {inserted}/{total} ({percentage:.1f}%)", end='\r')
            
        except Error as e:
            connection.rollback()
            print(f"\n   ✗ Errore batch: {e}")
            return False
    
    cursor.close()
    print(f"   ✓ {lang.upper()}: {inserted} traduzioni importate!     ")
    return True


def main():
    print("=" * 70)
    print("IMPORTAZIONE VELOCE - TRADUZIONI MTG")
    print("=" * 70)
    
    try:
        # Connetti
        connection = get_connection()
        
        # Lingue da importare (francese, tedesco, spagnolo, portoghese)
        languages = ['fr', 'de', 'es', 'pt']
        
        for lang in languages:
            if not import_language_bulk(connection, lang):
                print(f"   ⚠️ Saltato {lang}")
        
        connection.close()
        
        print()
        print("=" * 70)
        print("✓ IMPORTAZIONE COMPLETATA!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
