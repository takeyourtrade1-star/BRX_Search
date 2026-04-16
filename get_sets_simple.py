#!/usr/bin/env python3
"""
Script SEMPLICE per scaricare tutti i set da CardTrader API
Inserisci il token e basta!
"""

import json
import requests

# INSERISCI QUI IL TOKEN NUOVO
TOKEN = "eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJjYXJkdHJhZGVyLXByb2R1Y3Rpb24iLCJzdWIiOiJhcHA6MTk0NzgiLCJhdWQiOiJhcHA6MTk0NzgiLCJleHAiOjQ5MjYwNDQ3NDcsImp0aSI6ImM0MTczN2Y2LTFmZDEtNDJlNC04MTljLTc2YWMwMjAzYjQxZCIsImlhdCI6MTc3MDM3MTE0NywibmFtZSI6Ikp1bGlhblIgQXBwIDIwMjYwMjA2MTA0MjI3In0.LKfwR403r1pCZdl-5yQDZhE3rMFhCzycNH7XiK1ipFxYQnYnXOCibgVGy56IfH_Q06I1aZjWOVwxNeTEsLEgHm6P3dkFS2BVhcJBRdLl8GU3P2bDE6b6Z0n01ZbgIhWQd401lrW5_nR3RiyiUVniT9vsgLqft3y2W9BOAnMvl4_FSRDKOqKqe3xIvNQxYW1JRK9I0TmNxPdaGVRnyGnp_erbqGW2QwWV6XF-DjLs2z75zQ-HkOmt24VvMBKKto_DTkfl0MNzkJlnU3O4qnZKOCixMyyuIkGJH7fAGkFIKh11nUVMmAtFnAjfMjXvjnU0ZGTqL8SD_dmpI6-sXJb-fA"

# URL
URL = "https://api.cardtrader.com/api/v2/expansions"

print("=" * 70)
print("DOWNLOAD SET DA CARDTRADER")
print("=" * 70)
print()

# Verifica token
if TOKEN == "INSERISCI_IL_TOKEN_QUI":
    print("❌ ERRORE: Inserisci il token!")
    print()
    print("Passi:")
    print("1. Vai a https://www.cardtrader.com/api")
    print("2. Genera un nuovo token")
    print("3. Copia il token (lungo string)")
    print('4. Sostituisci "INSERISCI_IL_TOKEN_QUI" con il token')
    print()
    exit(1)

# Header
headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Accept': 'application/json'
}

print(f"🔗 Connessione a {URL}...")
print()

try:
    # Richiesta
    response = requests.get(URL, headers=headers, timeout=30)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        # Successo!
        data = response.json()
        
        print(f"✓ Scaricati {len(data)} set!")
        print()
        
        # Mostra primi 3
        print("📋 Primi 3 set:")
        for i, exp in enumerate(data[:3], 1):
            print(f"   {i}. {exp['name']} (code: {exp['code']}, game_id: {exp['game_id']})")
        
        print()
        
        # Salva in JSON
        with open('sets_da_cardtrader.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("✓ Salvati in 'sets_da_cardtrader.json'")
        print()
        print("=" * 70)
        print("✓ FATTO!")
        print("=" * 70)
        
    else:
        print(f"❌ ERRORE: Status {response.status_code}")
        print(f"Messaggio: {response.text}")

except Exception as e:
    print(f"❌ ERRORE: {e}")
