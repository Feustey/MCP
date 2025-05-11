#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour envoyer le plan d'action Feustey sur Telegram
"""

import os
import sys
import requests
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

def send_document_to_telegram(bot_token, chat_id, file_path, caption=None):
    """
    Envoie un document sur Telegram
    
    Args:
        bot_token (str): Token du bot Telegram
        chat_id (str): ID du chat ou @nom_canal
        file_path (str): Chemin vers le fichier à envoyer
        caption (str, optional): Légende du document
    
    Returns:
        bool: True si l'envoi a réussi, False sinon
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"Erreur: Le fichier {file_path} n'existe pas.")
            return False
        
        with open(file_path, 'rb') as file:
            files = {'document': file}
            data = {'chat_id': chat_id}
            
            if caption:
                data['caption'] = caption
                
            response = requests.post(url, data=data, files=files)
            
        if response.status_code == 200:
            print(f"Document envoyé avec succès à {chat_id}")
            return True
        else:
            print(f"Erreur lors de l'envoi du document: {response.status_code}, {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception lors de l'envoi du document: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Envoie un document sur Telegram")
    parser.add_argument("--token", help="Token du bot Telegram")
    parser.add_argument("--chat_id", help="ID du chat ou @nom_canal")
    parser.add_argument("--file", help="Chemin vers le fichier à envoyer", 
                        default="rag/RAG_assets/plans/plan_optimisation_feustey.md")
    parser.add_argument("--caption", help="Légende du document", 
                        default="Plan d'action pour l'optimisation du nœud Feustey")
    
    args = parser.parse_args()
    
    # Utiliser les arguments CLI ou les variables d'environnement
    bot_token = args.token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = args.chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token:
        print("Erreur: Token du bot Telegram manquant. Utilisez --token ou définissez TELEGRAM_BOT_TOKEN.")
        return 1
        
    if not chat_id:
        print("Erreur: ID du chat Telegram manquant. Utilisez --chat_id ou définissez TELEGRAM_CHAT_ID.")
        return 1
    
    success = send_document_to_telegram(bot_token, chat_id, args.file, args.caption)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 