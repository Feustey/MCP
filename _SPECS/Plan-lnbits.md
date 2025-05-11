
# Démarrage de la Phase 1 : Harmonisation et audit des clients LNBits

Pour commencer la mise en œuvre de la Phase 1, voici un plan d'action détaillé et concret :

## Étape 1 : Audit des implémentations existantes

Ran tool
1. **Analyse comparative des 3 implémentations identifiées** :
   - Créer un tableau comparatif des méthodes disponibles dans chaque client
   - Identifier les différences d'authentification et de gestion d'erreurs
   - Établir une liste des endpoints utilisés par chaque implémentation

2. **Actions immédiates** :
   - Créer un répertoire dédié pour le nouveau client unifié: `src/unified_clients/`
   - Préparer le squelette du fichier `unified_lnbits_client.py`
   - Mettre en place un système de logging avancé pour tracer les appels API

3. **Outils d'audit à développer** :
   ```python
   # Script d'analyse des clients existants (à créer)
   import ast
   import os
   
   def analyze_client_file(filepath):
       """Analyse un fichier client LNBits et extrait ses méthodes et endpoints"""
       with open(filepath, 'r') as f:
           code = f.read()
       
       # Utiliser l'AST pour extraire la structure du code
       tree = ast.parse(code)
       
       # Extraire les méthodes et endpoints
       methods = []
       endpoints = []
       
       for node in ast.walk(tree):
           # Trouver les définitions de méthodes
           if isinstance(node, ast.AsyncFunctionDef):
               methods.append(node.name)
           
           # Chercher les appels d'API dans les chaînes de caractères
           if isinstance(node, ast.Str) and ('api' in node.s.lower() or '/v1/' in node.s):
               endpoints.append(node.s)
       
       return {
           'filename': os.path.basename(filepath),
           'methods': methods,
           'endpoints': endpoints
       }
   
   # Analyser les 3 clients
   clients = [
       "/Users/stephanecourant/Documents/DAZ/MCP/MCP/mcp/lnbits_client.py",
       "/Users/stephanecourant/Documents/DAZ/MCP/MCP/src/lnbits_client.py",
       "/Users/stephanecourant/Documents/DAZ/MCP/MCP/src/clients/lnbits_client.py"
   ]
   
   results = [analyze_client_file(client) for client in clients]
   print(results)
   ```

## Étape 2 : Conception du client unifié

Read file: /Users/stephanecourant/Documents/DAZ/MCP/MCP/src/lnbits_client.py

Read file: /Users/stephanecourant/Documents/DAZ/MCP/MCP/mcp/lnbits_client.py
1. **Structure du client unifié** :
   ```python
   # src/unified_clients/unified_lnbits_client.py (à créer)
   
   import httpx
   import logging
   import asyncio
   import json
   from datetime import datetime, timedelta
   from typing import Dict, List, Any, Optional, Tuple, Set, Union
   from enum import Enum
   
   # Configuration du logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   
   class AuthMethod(Enum):
       API_KEY = "api_key"  # X-Api-Key header
       BEARER = "bearer"    # Authorization: Bearer
   
   class RetryConfig:
       def __init__(self, max_retries=3, base_delay=1.0, max_delay=30.0):
           self.max_retries = max_retries
           self.base_delay = base_delay
           self.max_delay = max_delay
   
   class LNBitsClientError(Exception):
       """Exception personnalisée pour les erreurs du client LNbits."""
       pass
   
   class UnifiedLNBitsClient:
       """
       Client unifié pour interagir avec l'API LNbits.
       Combine les fonctionnalités des différents clients existants.
       """
       def __init__(
           self,
           endpoint: str,
           api_key: str,
           admin_key: Optional[str] = None,
           invoice_key: Optional[str] = None,
           auth_method: AuthMethod = AuthMethod.API_KEY,
           retry_config: Optional[RetryConfig] = None,
           timeout: float = 30.0
       ):
           """
           Initialise le client LNbits.
   
           Args:
               endpoint: L'URL de base de l'instance LNbits
               api_key: La clé API principale pour l'authentification
               admin_key: La clé admin optionnelle
               invoice_key: La clé invoice optionnelle
               auth_method: Méthode d'authentification à utiliser
               retry_config: Configuration des tentatives de nouvelle connexion
               timeout: Timeout en secondes
           """
           if not endpoint or not api_key:
               raise ValueError("L'endpoint LNbits et la clé API sont requis.")
   
           self.endpoint = endpoint.rstrip('/')
           self.api_key = api_key
           self.admin_key = admin_key or api_key
           self.invoice_key = invoice_key or api_key
           self.auth_method = auth_method
           self.retry_config = retry_config or RetryConfig()
           self.timeout = timeout
   
           # Construction des en-têtes selon la méthode d'authentification
           self._build_headers()
   
           # Création du client HTTP
           self.client = httpx.AsyncClient(
               base_url=self.endpoint,
               timeout=self.timeout
           )
   
           logger.info(f"Client LNBits unifié initialisé avec endpoint: {self.endpoint}")
   
       def _build_headers(self):
           """Construit les en-têtes selon la méthode d'authentification."""
           self.headers = {}
           self.admin_headers = {}
           self.invoice_headers = {}
   
           # En-têtes communs
           common_headers = {
               "Content-Type": "application/json"
           }
   
           # En-têtes spécifiques selon la méthode d'authentification
           if self.auth_method == AuthMethod.API_KEY:
               self.headers = {**common_headers, "X-Api-Key": self.api_key}
               self.admin_headers = {**common_headers, "X-Api-Key": self.admin_key}
               self.invoice_headers = {**common_headers, "X-Api-Key": self.invoice_key}
           else:  # AuthMethod.BEARER
               self.headers = {**common_headers, "Authorization": f"Bearer {self.api_key}"}
               self.admin_headers = {**common_headers, "Authorization": f"Bearer {self.admin_key}"}
               self.invoice_headers = {**common_headers, "Authorization": f"Bearer {self.invoice_key}"}
   
       # [Suite du code avec toutes les méthodes unifiées]
   ```

2. **Implémentation des méthodes principales** :
   - Combiner les fonctionnalités des deux clients existants
   - Normaliser les signatures et types de retour
   - Ajouter une gestion d'erreur robuste avec retry

## Étape 3 : Mise en place des tests

1. **Structure des tests** :
   ```
   tests/
   └── unit/
       └── clients/
           ├── __init__.py
           ├── test_unified_lnbits_client.py
           └── mock_responses/
               ├── get_wallet_info.json
               ├── payments.json
               └── channels.json
   ```

2. **Script de test à développer** :
   ```python
   # tests/unit/clients/test_unified_lnbits_client.py (à créer)
   
   import pytest
   import asyncio
   import json
   import os
   from unittest.mock import patch, MagicMock
   
   from src.unified_clients.unified_lnbits_client import UnifiedLNBitsClient, LNBitsClientError, AuthMethod
   
   # Charger les réponses mockées
   @pytest.fixture
   def mock_responses():
       responses = {}
       mock_dir = os.path.join(os.path.dirname(__file__), "mock_responses")
       
       for filename in os.listdir(mock_dir):
           if filename.endswith(".json"):
               with open(os.path.join(mock_dir, filename), "r") as f:
                   responses[filename[:-5]] = json.load(f)
       
       return responses
   
   @pytest.fixture
   def client():
       # Créer un client de test avec des valeurs factices
       return UnifiedLNBitsClient(
           endpoint="https://test.lnbits.com",
           api_key="test_api_key",
           admin_key="test_admin_key",
           invoice_key="test_invoice_key"
       )
   
   @pytest.mark.asyncio
   async def test_get_wallet_info(client, mock_responses):
       # Mock de la réponse HTTP
       with patch("httpx.AsyncClient.request") as mock_request:
           mock_response = MagicMock()
           mock_response.status_code = 200
           mock_response.json.return_value = mock_responses["get_wallet_info"]
           mock_request.return_value = mock_response
           
           # Appel de la méthode à tester
           result = await client.get_wallet_info()
           
           # Vérifications
           assert result == mock_responses["get_wallet_info"]
           mock_request.assert_called_once()
   
   @pytest.mark.asyncio
   async def test_retry_mechanism(client):
       # Test du mécanisme de retry
       with patch("httpx.AsyncClient.request") as mock_request:
           # Simuler 2 échecs puis un succès
           mock_error_response = MagicMock()
           mock_error_response.raise_for_status.side_effect = httpx.RequestError("Connection error")
           
           mock_success_response = MagicMock()
           mock_success_response.status_code = 200
           mock_success_response.json.return_value = {"success": True}
           
           mock_request.side_effect = [
               mock_error_response,
               mock_error_response,
               mock_success_response
           ]
           
           # La méthode devrait réussir après les retries
           result = await client.get_wallet_info()
           
           assert result == {"success": True}
           assert mock_request.call_count == 3
   ```

## Étape 4 : Documentation

1. **Structure de documentation** :
   - Créer un document Markdown dans `docs/api/lnbits_client.md`
   - Décrire toutes les méthodes et leurs paramètres
   - Fournir des exemples d'utilisation

2. **Exemple de documentation** :
   ```markdown
   # Client LNBits Unifié
   
   Ce client fournit une interface unifiée pour interagir avec l'API LNBits.
   
   ## Initialisation
   
   ```python
   from src.unified_clients.unified_lnbits_client import UnifiedLNBitsClient, AuthMethod
   
   # Initialisation standard avec clé API
   client = UnifiedLNBitsClient(
       endpoint="https://your-lnbits-instance.com",
       api_key="your_api_key"
   )
   
   # Initialisation avec clés séparées
   client_advanced = UnifiedLNBitsClient(
       endpoint="https://your-lnbits-instance.com",
       api_key="general_api_key",
       admin_key="admin_key",
       invoice_key="invoice_key",
       auth_method=AuthMethod.BEARER  # Utiliser Authorization: Bearer
   )
   ```
   
   ## API Wallet
   
   ### get_wallet_info()
   
   Récupère les informations du wallet LNBits.
   
   ```python
   wallet_info = await client.get_wallet_info()
   print(f"Solde: {wallet_info['balance']} sats")
   ```
   
   [...]
   ```

## Actions Immédiates à Entreprendre

1. **Créer la structure de fichiers** :
   ```bash
   mkdir -p src/unified_clients
   touch src/unified_clients/__init__.py
   touch src/unified_clients/unified_lnbits_client.py
   
   mkdir -p tests/unit/clients/mock_responses
   touch tests/unit/clients/__init__.py
   touch tests/unit/clients/test_unified_lnbits_client.py
   ```

2. **Préparer des données de test** :
   - Extraire des exemples de réponses des API existantes
   - Créer les fichiers JSON de mock dans le répertoire approprié

3. **Développer le script d'analyse comparatif** pour guider le développement du client unifié

4. **Planning des réunions de revue** :
   - Revue de conception avec l'équipe (fin de semaine 1)
   - Revue de code après implémentation du client de base
   - Démonstration des tests automatisés

Ce plan détaillé vous permet de démarrer immédiatement la Phase 1 avec des actions concrètes et une vision claire du résultat attendu.
