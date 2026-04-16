#!/usr/bin/env python3
"""
Script CORRETTO per popolare set_translations.
Matcha per cardtrader_id e poi inserisce le traduzioni.
"""

import json
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


def get_connection():
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
        print(f"✓ Connesso")
        return conn
    except Error as e:
        print(f"✗ ERRORE: {e}")
        raise


def load_sets_from_cardtrader():
    with open('sets_da_cardtrader.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def insert_translations_corrected(connection, ct_sets):
    """
    Inserisci traduzioni usando il JOIN corretto.
    """
    print()
    print("📝 INSERT TRADUZIONI (con JOIN corretto)...")
    
    languages = ['it', 'fr', 'de', 'es', 'pt']
    cursor = connection.cursor()
    
    # Usa INNER JOIN per matchare correttamente
    # Crea una lista di (cardtrader_id, name, code, language)
    insert_data = []
    
    for ct_set in ct_sets:
        ct_id = ct_set['id']  # Questo è l'ID di CardTrader
        name = ct_set['name']
        code = ct_set['code']
        
        for lang in languages:
            insert_data.append((ct_id, lang, name, code))
    
    # Usa INSERT con JOIN per trovare il set_id corretto
    query = """
        INSERT INTO set_translations (set_id, language_code, translated_name, set_code)
        SELECT 
            s.id,
            %s,
            %s,
            %s
        FROM sets s
        WHERE s.cardtrader_id = %s
        ON DUPLICATE KEY UPDATE translated_name = VALUES(translated_name)
    """
    
    total = 0
    errors = 0
    
    for i, (ct_id, lang, name, code) in enumerate(insert_data):
        try:
            cursor.execute(query, (lang, name, code, ct_id))
            total += 1
            
            if (i + 1) % 500 == 0:
                percentage = ((i + 1) / len(insert_data)) * 100
                print(f"   {percentage:.1f}% ({i+1}/{len(insert_data)})", end='\r')
                connection.commit()
                
        except Error as e:
            errors += 1
            if errors < 5:  # Mostra solo i primi 5 errori
                print(f"\n   ✗ Errore: {e}")
    
    connection.commit()
    cursor.close()
    
    print(f"\n✓ Inserite {total} traduzioni (errori: {errors})")
    return total, errors


def main():
    print("=" * 70)
    print("POPOLA SET_TRANSLATIONS - VERSIONE CORRETTA")
    print("=" * 70)
    print()
    
    try:
        print("1. Caricamento dati...")
        ct_sets = load_sets_from_cardtrader()
        print(f"✓ Caricate {len(ct_sets)} set")
        
        print("\n2. Connessione al DB...")
        connection = get_connection()
        
        print("\n3. Inserimento traduzioni...")
        total, errors = insert_translations_corrected(connection, ct_sets)
        
        connection.close()
        
        print()
        print("=" * 70)
        print("✓ COMPLETATO!")
        print("=" * 70)
        print()
        print(f"✓ Traduzioni inserite: {total}")
        if errors > 0:
            print(f"⚠️  Errori: {errors}")
        
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
