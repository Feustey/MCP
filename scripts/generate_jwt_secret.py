#!/usr/bin/env python3
"""
Script de génération de clé JWT sécurisée pour MCP
Dernière mise à jour: 7 janvier 2025
"""

import secrets
import base64
import os

def generate_jwt_secret(length: int = 32) -> str:
    """Génère une clé JWT sécurisée"""
    return base64.b64encode(secrets.token_bytes(length)).decode('utf-8')

def main():
    # Générer la clé
    jwt_secret = generate_jwt_secret()
    
    # Afficher les instructions
    print("\n=== Génération de clé JWT pour MCP ===")
    print("\nNouvelle clé JWT générée :")
    print(f"\n{jwt_secret}\n")
    print("Instructions :")
    print("1. Ajoutez cette clé à votre fichier .env :")
    print(f'JWT_SECRET="{jwt_secret}"')
    print("\n2. Ou exportez-la directement dans votre environnement :")
    print(f'export JWT_SECRET="{jwt_secret}"')
    print("\nATTENTION : Conservez cette clé de manière sécurisée !")
    print("Ne la partagez jamais et ne la committez pas dans Git.")

if __name__ == "__main__":
    main() 