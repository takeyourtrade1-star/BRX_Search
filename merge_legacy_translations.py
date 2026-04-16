#!/usr/bin/env python3
"""
Script per popolare le traduzioni MTG dai dati legacy.
Legge i file di lingua dal vecchio DB e popola i template con match preciso su oracle_id.
"""

import json
import os
from datetime import datetime
from collections import defaultdict


# Configurazione percorsi
LEGACY_LANG_MAPS_DIR = 'data_vecchio_db/lang-maps'
MTG_CARDS_FILE = 'output/mtg-cards/mtg_cards.json'
OUTPUT_DIR = 'output/mtg-cards'

# Lingue da processare
LANGUAGES = ['it', 'fr', 'de', 'es', 'pt']


def load_legacy_translations(lang):
    """
    Carica le traduzioni dal vecchio DB per una lingua specifica.
    Formato legacy: [{"id": "oracle_id", "name": "english", "preferred": "tradotto"}, ...]
    Ritorna: {oracle_id: translated_name}
    """
    filepath = os.path.join(LEGACY_LANG_MAPS_DIR, f'{lang}.json')
    
    if not os.path.exists(filepath):
        print(f"   ⚠️  File non trovato: {filepath}")
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Converti da lista a dizionario {oracle_id: translated_name}
        translations = {}
        for entry in data:
            oracle_id = entry.get('id')
            translated_name = entry.get('preferred')
            
            if oracle_id and translated_name:
                translations[oracle_id] = translated_name
        
        print(f"   ✓ Caricate {len(translations)} traduzioni da {lang}.json")
        return translations
        
    except Exception as e:
        print(f"   ❌ Errore lettura {lang}.json: {e}")
        return {}


def load_mtg_cards():
    """
    Carica le carte MTG dal DB attuale.
    Formato: {oracle_id: {name: "english_name", game_slug: "mtg"}}
    """
    if not os.path.exists(MTG_CARDS_FILE):
        raise FileNotFoundError(f"File non trovato: {MTG_CARDS_FILE}")
    
    with open(MTG_CARDS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✓ Caricate {len(data)} carte MTG dal DB attuale")
    return data


def load_translation_template(lang):
    """
    Carica il template vuoto per una lingua.
    """
    template_file = os.path.join(OUTPUT_DIR, f'mtg_translations_{lang}_TEMPLATE.json')
    
    if not os.path.exists(template_file):
        raise FileNotFoundError(f"Template non trovato: {template_file}")
    
    with open(template_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def merge_translations(mtg_cards, legacy_translations, lang):
    """
    Mergia le traduzioni legacy con le carte attuali.
    Ritorna: dizionario con traduzioni compilate e statistiche di match.
    """
    merged = {}
    stats = {
        'total_cards': len(mtg_cards),
        'translated': 0,
        'missing': 0,
        'no_translation': 0
    }
    
    for oracle_id, card_info in mtg_cards.items():
        entry = {
            'english_name': card_info['name'],
            'translated_name': legacy_translations.get(oracle_id, ''),
            'language': lang,
            'game_slug': 'mtg'
        }
        
        merged[oracle_id] = entry
        
        if entry['translated_name']:
            stats['translated'] += 1
        else:
            stats['missing'] += 1
    
    return merged, stats


def save_populated_translations(merged_data, lang, stats):
    """
    Salva il file di traduzioni compilato.
    """
    output_file = os.path.join(OUTPUT_DIR, f'mtg_translations_{lang}.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2, sort_keys=True)
    
    print(f"   ✓ Salvato: {output_file}")
    
    # Salva statistiche
    stats_file = os.path.join(OUTPUT_DIR, f'mtg_translations_{lang}_STATS.json')
    stats_data = {
        'language': lang,
        'timestamp': datetime.now().isoformat(),
        'total_cards': stats['total_cards'],
        'translated_cards': stats['translated'],
        'missing_translations': stats['missing'],
        'coverage_percentage': round((stats['translated'] / stats['total_cards'] * 100), 2)
    }
    
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, ensure_ascii=False, indent=2)
    
    print(f"   ✓ Statistiche salvate: {stats_file}")
    
    return stats_data


def main():
    """
    Funzione principale
    """
    print("=" * 70)
    print("Merge Traduzioni MTG da DB Legacy")
    print("=" * 70)
    print()
    
    try:
        # 1. Carica le carte MTG attuali
        print("1. Caricamento carte MTG attuali...")
        mtg_cards = load_mtg_cards()
        print()
        
        # 2. Per ogni lingua, fai il merge
        print("2. Processamento lingue...")
        print()
        
        all_stats = {}
        
        for lang in LANGUAGES:
            print(f"   📍 Lingua: {lang}")
            
            # Carica traduzioni legacy
            legacy_translations = load_legacy_translations(lang)
            
            if not legacy_translations:
                print(f"   ⚠️  Nessuna traduzione trovata per {lang}, skip")
                print()
                continue
            
            # Merge
            merged, stats = merge_translations(mtg_cards, legacy_translations, lang)
            
            # Salva
            stats_data = save_populated_translations(merged, lang, stats)
            all_stats[lang] = stats_data
            
            print()
        
        # 3. Rapporto finale
        print("=" * 70)
        print("📊 RAPPORTO DI COPERTURA")
        print("=" * 70)
        print()
        
        for lang in LANGUAGES:
            if lang in all_stats:
                s = all_stats[lang]
                print(f"🌍 {lang.upper()}")
                print(f"   Total cards: {s['total_cards']}")
                print(f"   Translated: {s['translated_cards']}")
                print(f"   Missing: {s['missing_translations']}")
                print(f"   Coverage: {s['coverage_percentage']}%")
                print()
        
        print("=" * 70)
        print("[✓] COMPLETATO CON SUCCESSO!")
        print("=" * 70)
        
    except FileNotFoundError as e:
        print(f"\n❌ ERRORE: {e}")
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
