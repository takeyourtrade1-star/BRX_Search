#!/usr/bin/env python3
"""
Script per matchare i set da CardTrader API con il DB e aggiornare i nomi.
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


def load_sets_from_cardtrader():
    """Carica i set da CardTrader JSON"""
    try:
        with open('sets_da_cardtrader.json', 'r', encoding='utf-8') as f:
            sets = json.load(f)
        print(f"✓ Caricate {len(sets)} set da CardTrader")
        return sets
    except FileNotFoundError:
        print("✗ File 'sets_da_cardtrader.json' non trovato!")
        sys.exit(1)


def load_db_sets(connection):
    """Carica i set dal DB"""
    cursor = connection.cursor(dictionary=True)
    
    query = "SELECT id, cardtrader_id, name, game_id FROM sets"
    
    try:
        cursor.execute(query)
        sets = cursor.fetchall()
        cursor.close()
        
        print(f"✓ Caricate {len(sets)} set dal DB")
        return sets
        
    except Error as e:
        print(f"✗ ERRORE: {e}")
        raise


def match_and_update(connection, ct_sets, db_sets):
    """
    Matcha i set e aggiorna il DB.
    """
    # Crea dict per lookup rapido
    db_by_ct_id = {s['cardtrader_id']: s for s in db_sets if s['cardtrader_id']}
    ct_by_id = {s['id']: s for s in ct_sets}
    
    print()
    print("📊 MATCHING...")
    print()
    
    matched = 0
    not_matched = 0
    
    cursor = connection.cursor()
    
    # Per ogni set in CardTrader
    for ct_id, ct_set in ct_by_id.items():
        ct_name = ct_set['name']
        game_id = ct_set['game_id']
        
        # Cerca nel DB per cardtrader_id
        if ct_id in db_by_ct_id:
            db_set = db_by_ct_id[ct_id]
            db_id = db_set['id']
            old_name = db_set['name']
            
            if old_name != ct_name:
                # Aggiorna il nome
                update_query = "UPDATE sets SET name = %s WHERE id = %s"
                
                try:
                    cursor.execute(update_query, (ct_name, db_id))
                    matched += 1
                    
                    if matched <= 10:  # Mostra primi 10
                        print(f"   ✓ ID {db_id}: '{old_name}' → '{ct_name}'")
                    
                except Error as e:
                    print(f"   ✗ Errore update ID {db_id}: {e}")
            else:
                matched += 1
        else:
            not_matched += 1
    
    # Commit
    try:
        connection.commit()
        print()
        print(f"✓ Aggiornati {matched} set")
        print(f"⚠️  Non trovati {not_matched} set")
    except Error as e:
        connection.rollback()
        print(f"✗ ERRORE commit: {e}")
    
    cursor.close()
    
    return matched, not_matched


def populate_set_translations(connection, ct_sets):
    """
    Popola set_translations con i nomi di CardTrader.
    """
    cursor = connection.cursor()
    
    print()
    print("📝 POPOLO SET_TRANSLATIONS...")
    print()
    
    # Languages da usare
    languages = ['it', 'fr', 'de', 'es', 'pt']
    
    insert_query = """
        INSERT INTO set_translations (set_id, language_code, translated_name, set_code)
        SELECT id, %s, %s, %s FROM sets WHERE cardtrader_id = %s
        ON DUPLICATE KEY UPDATE translated_name = VALUES(translated_name)
    """
    
    total_inserted = 0
    
    for ct_set in ct_sets:
        ct_id = ct_set['id']
        name = ct_set['name']
        code = ct_set['code']
        
        # Inserisci per ogni lingua (stesso nome per ora)
        for lang in languages:
            try:
                cursor.execute(insert_query, (lang, name, code, ct_id))
                total_inserted += 1
            except Error as e:
                print(f"   ✗ Errore per {code} ({lang}): {e}")
    
    try:
        connection.commit()
        print(f"✓ Inserite {total_inserted} traduzioni")
    except Error as e:
        connection.rollback()
        print(f"✗ ERRORE commit: {e}")
    
    cursor.close()


def main():
    print("=" * 70)
    print("MATCH E UPDATE SET DAL DATABASE")
    print("=" * 70)
    print()
    
    try:
        # 1. Carica dati
        print("1. Caricamento dati...")
        ct_sets = load_sets_from_cardtrader()
        
        connection = get_connection()
        db_sets = load_db_sets(connection)
        print()
        
        # 2. Match e update
        print("2. Match e aggiornamento nomi...")
        matched, not_matched = match_and_update(connection, ct_sets, db_sets)
        
        # 3. Popola traduzioni
        print("\n3. Popolamento set_translations...")
        populate_set_translations(connection, ct_sets)
        
        connection.close()
        
        print()
        print("=" * 70)
        print("✓ COMPLETATO!")
        print("=" * 70)
        print()
        print(f"✓ Matched: {matched}")
        print(f"⚠️  Not matched: {not_matched}")
        print()
        print("Il DB è ora aggiornato con i nomi reali dei set!")
        
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
