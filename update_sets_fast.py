#!/usr/bin/env python3
"""
Script VELOCE per matchare e aggiornare i set in BATCH.
Usa UPDATE bulk invece di uno per uno.
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
        print(f"✓ Connesso")
        return conn
    except Error as e:
        print(f"✗ ERRORE: {e}")
        raise


def load_sets_from_cardtrader():
    """Carica i set da CardTrader JSON"""
    with open('sets_da_cardtrader.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def update_sets_fast(connection, ct_sets):
    """
    Aggiorna i nomi dei set in BATCH velocemente.
    Usa CASE/WHEN per UPDATE bulk.
    """
    print()
    print("🚀 UPDATE SETS IN BATCH...")
    
    cursor = connection.cursor()
    
    # Costruisci query CASE/WHEN
    case_parts = []
    for ct_set in ct_sets:
        ct_id = ct_set['id']
        name = ct_set['name'].replace("'", "\\'")
        case_parts.append(f"WHEN cardtrader_id = {ct_id} THEN '{name}'")
    
    case_clause = " ".join(case_parts)
    
    query = f"""
        UPDATE sets 
        SET name = CASE 
            {case_clause}
            ELSE name 
        END
        WHERE cardtrader_id IN ({','.join(str(s['id']) for s in ct_sets)})
    """
    
    try:
        cursor.execute(query)
        connection.commit()
        affected = cursor.rowcount
        print(f"✓ Aggiornati {affected} set")
        return affected
    except Error as e:
        connection.rollback()
        print(f"✗ ERRORE: {e}")
        return 0
    finally:
        cursor.close()


def insert_translations_bulk(connection, ct_sets):
    """
    Inserisci traduzioni in BULK per tutte le lingue.
    """
    print()
    print("📝 INSERT TRADUZIONI IN BULK...")
    
    languages = ['it', 'fr', 'de', 'es', 'pt']
    cursor = connection.cursor()
    
    # Costruisci VALUES clauses
    values_list = []
    for ct_set in ct_sets:
        ct_id = ct_set['id']
        name = ct_set['name'].replace("'", "\\'")
        code = ct_set['code'] if ct_set['code'] else 'NULL'
        
        for lang in languages:
            values_list.append(f"((SELECT id FROM sets WHERE cardtrader_id = {ct_id}), '{lang}', '{name}', '{code}')")
    
    # Inserisci in batch di 500
    batch_size = 500
    total_inserted = 0
    
    for i in range(0, len(values_list), batch_size):
        batch = values_list[i:i+batch_size]
        
        query = f"""
            INSERT INTO set_translations (set_id, language_code, translated_name, set_code)
            VALUES {','.join(batch)}
            ON DUPLICATE KEY UPDATE translated_name = VALUES(translated_name)
        """
        
        try:
            cursor.execute(query)
            connection.commit()
            total_inserted += len(batch)
            
            percentage = (total_inserted / len(values_list)) * 100
            print(f"   {percentage:.1f}% ({total_inserted}/{len(values_list)})", end='\r')
            
        except Error as e:
            connection.rollback()
            print(f"✗ Errore batch: {e}")
            continue
    
    cursor.close()
    print(f"\n✓ Inserite {total_inserted} traduzioni")
    return total_inserted


def main():
    print("=" * 70)
    print("MATCH E UPDATE SET - VERSIONE VELOCE")
    print("=" * 70)
    print()
    
    try:
        # Carica
        print("1. Caricamento dati...")
        ct_sets = load_sets_from_cardtrader()
        print(f"✓ Caricate {len(ct_sets)} set")
        
        # Connetti
        print("\n2. Connessione al DB...")
        connection = get_connection()
        
        # Update
        print("\n3. Aggiornamento nomi...")
        updated = update_sets_fast(connection, ct_sets)
        
        # Insert traduzioni
        print("\n4. Popolamento traduzioni...")
        inserted = insert_translations_bulk(connection, ct_sets)
        
        connection.close()
        
        print()
        print("=" * 70)
        print("✓ COMPLETATO!")
        print("=" * 70)
        print()
        print(f"✓ Set aggiornati: {updated}")
        print(f"✓ Traduzioni inserite: {inserted}")
        
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
