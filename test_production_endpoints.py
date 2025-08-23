import requests
import json

# Configuration
# VERCEL_URL supprimé - Utilisation exclusive d'Hostinger
API_KEY = "sk-prod_2b1e1e2e-6e7e-4b7e-8e2e-xxxxxxxxxxxx"  # <-- Remplacez par la vraie clé API
NODE_ID = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"  # feustey

# Obtenir un token
def get_token(base_url):
    response = requests.post(
        f"{base_url}/api/auth/token", 
        json={"api_key": API_KEY}
    )
    if response.status_code == 200:
        return response.json()["token"]
    else:
        print(f"Échec d'authentification: {response.status_code}")
        print(response.text)
        return None

# Exécuter les tests
def run_tests():
    token = get_token(VERCEL_URL)
    if not token:
        print("Impossible d'obtenir un token, arrêt des tests")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: État de santé
    health = requests.get(f"{VERCEL_URL}/health")
    print(f"\n1. Test de santé: {health.status_code}")
    print(health.json())
    
    # Test 2: Score du nœud
    score = requests.get(
        f"{VERCEL_URL}/api/v1/lightning/scores/{NODE_ID}",
        headers=headers
    )
    print(f"\n2. Score du nœud: {score.status_code}")
    if score.status_code == 200:
        print(json.dumps(score.json(), indent=2)[:500] + "...")
    else:
        print(score.text)
    
    # Test 3: Recommandations
    recommendations = requests.get(
        f"{VERCEL_URL}/api/v1/lightning/nodes/{NODE_ID}/recommendations",
        headers=headers
    )
    print(f"\n3. Recommandations: {recommendations.status_code}")
    if recommendations.status_code == 200:
        print(json.dumps(recommendations.json(), indent=2)[:500] + "...")
    else:
        print(recommendations.text)
    
    # Test 4: Requête RAG spécifique pour la modification des canaux
    rag_query = requests.post(
        f"{VERCEL_URL}/rag/query",
        headers=headers,
        json={
            "query": "Quelles modifications devraient être faites sur les canaux du nœud feustey pour optimiser ses performances? Détaille spécifiquement quels canaux fermer, ouvrir ou rééquilibrer.",
            "max_results": 5
        }
    )
    print(f"\n4. Requête RAG sur les modifications de canaux: {rag_query.status_code}")
    if rag_query.status_code == 200:
        print(json.dumps(rag_query.json(), indent=2)[:500] + "...")
    else:
        print(rag_query.text)

if __name__ == "__main__":
    run_tests() 