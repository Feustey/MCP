import os
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Récupérer les paramètres de connexion
lnbits_url = os.getenv("LNBITS_URL")
lnbits_user = os.getenv("LNBITS_USER")
lnbits_password = os.getenv("LNBITS_PASSWORD")

print(f"Tentative de connexion à LNBits à l'adresse : {lnbits_url}")

try:
    # Tenter de se connecter à l'API de santé de LNBits
    response = requests.get(f"{lnbits_url}/api/v1/health", verify=False)
    
    if response.status_code == 200:
        print("Connexion à LNBits réussie !")
        print(f"Réponse : {response.json()}")
    else:
        print(f"Erreur de connexion. Code de statut : {response.status_code}")
        print(f"Réponse : {response.text}")
except Exception as e:
    print(f"Erreur lors de la connexion à LNBits : {str(e)}")
    
    # Essayer avec HTTP au lieu de HTTPS
    try:
        http_url = lnbits_url.replace("https://", "http://")
        print(f"\nTentative de connexion à LNBits avec HTTP : {http_url}")
        response = requests.get(f"{http_url}/api/v1/health", verify=False)
        
        if response.status_code == 200:
            print("Connexion à LNBits réussie avec HTTP !")
            print(f"Réponse : {response.json()}")
        else:
            print(f"Erreur de connexion avec HTTP. Code de statut : {response.status_code}")
            print(f"Réponse : {response.text}")
    except Exception as e2:
        print(f"Erreur lors de la connexion à LNBits avec HTTP : {str(e2)}") 