#!/usr/bin/env python3
"""
Script per creare la tabella set_translations nel database.
Simile a card_translations ma per i set (nomi tradotti).
"""

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


def create_set_translations_table(connection):
    """Crea la tabella set_translations"""
    cursor = connection.cursor()
    
    create_table_query = """
        CREATE TABLE IF NOT EXISTS set_translations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            set_id INT NOT NULL,
            language_code VARCHAR(5) NOT NULL,
            translated_name VARCHAR(255) NOT NULL,
            set_code VARCHAR(20),
            set_symbol_svg LONGTEXT,
            
            -- Indici per ricerca veloce
            INDEX idx_set_language (set_id, language_code),
            INDEX idx_language (language_code),
            
            -- Vincolo: una traduzione per set e lingua
            UNIQUE KEY unique_set_translation (set_id, language_code),
            
            -- Relazione con tabella sets
            CONSTRAINT fk_set_id FOREIGN KEY (set_id) REFERENCES sets(id) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """
    
    try:
        cursor.execute(create_table_query)
        connection.commit()
        print("✓ Tabella 'set_translations' creata/verificata")
        return True
        
    except Error as e:
        print(f"✗ ERRORE nella creazione della tabella: {e}")
        return False
    
    finally:
        cursor.close()


def verify_table_structure(connection):
    """Verifica la struttura della tabella creata"""
    cursor = connection.cursor()
    
    query = "DESCRIBE set_translations"
    
    try:
        cursor.execute(query)
        columns = cursor.fetchall()
        
        print()
        print("📋 Struttura tabella set_translations:")
        print()
        for col in columns:
            col_name = col[0]
            col_type = col[1]
            null_constraint = col[2]
            key = col[3]
            print(f"   {col_name:20} {col_type:20} {null_constraint:3} {key}")
        
        return True
        
    except Error as e:
        print(f"✗ ERRORE nella verifica: {e}")
        return False
    
    finally:
        cursor.close()


def main():
    print("=" * 70)
    print("CREAZIONE TABELLA SET_TRANSLATIONS")
    print("=" * 70)
    print()
    
    try:
        # Connetti
        print("1. Connessione al database...")
        connection = get_connection()
        print()
        
        # Crea tabella
        print("2. Creazione tabella...")
        if create_set_translations_table(connection):
            print()
            
            # Verifica
            print("3. Verifica struttura...")
            verify_table_structure(connection)
        
        connection.close()
        
        print()
        print("=" * 70)
        print("✓ COMPLETATO!")
        print("=" * 70)
        print()
        print("La tabella set_translations è pronta per ricevere i dati.")
        print()
        print("Campi:")
        print("  - set_id: Riferimento a sets.id")
        print("  - language_code: it, fr, de, es, pt")
        print("  - translated_name: Nome tradotto del set")
        print("  - set_code: Codice del set (es: IKO)")
        print("  - set_symbol_svg: SVG dell'icona del set")
        
    except Exception as e:
        print(f"\n✗ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
