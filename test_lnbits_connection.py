import os
import requests
import urllib3
import json
from dotenv import load_dotenv

# Désactiver les avertissements pour les certificats SSL non vérifiés
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Charger les variables d'environnement
load_dotenv()

# Récupérer les paramètres de connexion ou utiliser des valeurs par défaut
# Liste d'URLs potentielles pour LNBits
lnbits_instances = [
    {"url": "https://legend.lnbits.com", "name": "Instance Legend"},
    {"url": "https://testnet.lnbits.com", "name": "Instance Testnet"},
    {"url": "http://192.168.0.45:5000", "name": "Adresse locale spécifiée"},
    {"url": "http://localhost:5000", "name": "Localhost standard"}
]

lnbits_wallet_id = os.getenv("LNBITS_WALLET_ID", "ab6380529b624321ade9ccb2aae3646b")
lnbits_admin_key = os.getenv("LNBITS_ADMIN_KEY", "a271475725244124a5997ead1c7deb39")
lnbits_invoice_key = os.getenv("LNBITS_INVOICE_KEY", "6139932367744b4abaf4c83a5113aca4")

print(f"Wallet ID : {lnbits_wallet_id}")
print(f"Clé Admin : {lnbits_admin_key}")
print(f"Clé Invoice : {lnbits_invoice_key}")
print(f"Tentative de connexion à différentes instances LNBits...")

# Endpoints à tester pour vérifier la disponibilité
endpoints_to_test = [
    "/api/v1/health",  # Endpoint standard
    "/"                # Page d'accueil
]

# Test des différentes instances LNBits
lnbits_url = None
for instance in lnbits_instances:
    instance_url = instance["url"]
    print(f"\n--- Test de connexion à l'instance LNBits: {instance['name']} ({instance_url}) ---")
    
    # Tester différents endpoints
    for endpoint in endpoints_to_test:
        try:
            full_url = f"{instance_url}{endpoint}"
            print(f"Tentative avec l'endpoint: {full_url}")
            response = requests.get(full_url, verify=False, timeout=15)
            
            if response.status_code in [200, 201, 202]:
                print(f"✅ Connexion réussie à {full_url} ! Code: {response.status_code}")
                lnbits_url = instance_url
                # Endpoint trouvé, sortir de la boucle
                break
            else:
                print(f"❌ Erreur de connexion à {full_url}. Code: {response.status_code}")
        except Exception as e:
            print(f"❌ Erreur lors de la connexion à {full_url} : {str(e)}")
    
    # Si une URL fonctionnelle a été trouvée, sortir de la boucle des instances
    if lnbits_url:
        print(f"\n✅ Instance LNBits fonctionnelle trouvée: {lnbits_url}")
        break
else:
    print("\n❌ Aucune instance LNBits n'est accessible. Impossible de continuer les tests.")

# Test des endpoints authentifiés si une URL fonctionnelle a été trouvée
if lnbits_url:
    print("\n--- Test des endpoints authentifiés ---")
    
    # Liste des endpoints à tester
    authenticated_endpoints = [
        {
            "name": "Wallet Info",
            "url": f"{lnbits_url}/api/v1/wallet",
            "method": "GET",
            "headers": {"X-Api-Key": lnbits_admin_key},
            "data": None
        },
        {
            "name": "Create Invoice",
            "url": f"{lnbits_url}/api/v1/payments",
            "method": "POST",
            "headers": {"X-Api-Key": lnbits_invoice_key},
            "data": {"out": False, "amount": 10, "memo": "Test invoice"}
        }
    ]
    
    for endpoint in authenticated_endpoints:
        print(f"\nTest de l'endpoint: {endpoint['name']} ({endpoint['url']})")
        try:
            headers = endpoint['headers']
            headers["Content-type"] = "application/json"
            
            print(f"Headers: {json.dumps(headers)}")
            
            if endpoint['data']:
                print(f"Data: {json.dumps(endpoint['data'])}")
            
            if endpoint['method'] == "GET":
                response = requests.get(
                    endpoint['url'],
                    headers=headers,
                    verify=False,
                    timeout=15
                )
            elif endpoint['method'] == "POST":
                response = requests.post(
                    endpoint['url'],
                    headers=headers,
                    json=endpoint['data'],
                    verify=False,
                    timeout=15
                )
            
            print(f"Code de statut: {response.status_code}")
            
            if response.status_code in [200, 201, 202]:
                print(f"✅ Appel à {endpoint['name']} réussi !")
                try:
                    response_data = response.json()
                    print(f"Réponse: {json.dumps(response_data, indent=2)[:500]}...")
                except:
                    print(f"Réponse (non-JSON): {response.text[:500]}...")
            else:
                print(f"❌ Erreur lors de l'appel à {endpoint['name']}. Code: {response.status_code}")
                print(f"Réponse: {response.text[:500]}")
        except Exception as e:
            print(f"❌ Exception lors de l'appel à {endpoint['name']}: {str(e)}")
else:
    print("\n❌ Impossible de tester les endpoints authentifiés: aucune instance LNBits accessible.") 