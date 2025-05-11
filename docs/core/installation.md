# Documentation d'installation
> Dernière mise à jour: 7 mai 2025

# Installation

## Prérequis

- Python 3.9 ou supérieur
- MongoDB Community Edition
- Redis
- pip (gestionnaire de paquets Python)

## Installation des dépendances système

### MongoDB

1. Installer MongoDB Community Edition via Homebrew :
```bash
brew tap mongodb/brew
brew install mongodb-community
```

2. Démarrer le service MongoDB :
```bash
brew services start mongodb-community
```

### Redis

1. Installer Redis via Homebrew :
```bash
brew install redis
```

2. Démarrer le service Redis :
```bash
brew services start redis
```

## Installation du projet

1. Cloner le dépôt :
```bash
git clone https://github.com/votre-username/mcp.git
cd mcp
```

2. Créer et activer un environnement virtuel :
```bash
python -m venv .venv
source .venv/bin/activate  # Sur Unix/macOS
# ou
.venv\Scripts\activate  # Sur Windows
```

3. Installer les dépendances Python :
```bash
pip install -r requirements.txt
```

4. Configurer les variables d'environnement :
```bash
cp .env.example .env
```
Puis éditer le fichier `.env` avec vos clés API et configurations :
```
MONGODB_URI=mongodb://localhost:27017/mcp
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=votre_clé_api_openai
```

## Vérification de l'installation

1. Vérifier que MongoDB est en cours d'exécution :
```bash
mongosh
```

2. Vérifier que Redis est en cours d'exécution :
```bash
redis-cli ping
```

3. Exécuter les tests :
```bash
python -m pytest tests/ -v
```

## Dépannage

### MongoDB ne démarre pas
- Vérifier les logs : `brew services list`
- Redémarrer le service : `brew services restart mongodb-community`

### Redis ne démarre pas
- Vérifier les logs : `brew services list`
- Redémarrer le service : `brew services restart redis`

### Erreurs de connexion
- Vérifier que les services sont en cours d'exécution
- Vérifier les variables d'environnement dans `.env`
- Vérifier les logs des services 

## Exigences système

- Python 3.8+
- MongoDB 4.4+
- Redis 6.2+
- LND v0.16.1-beta+ (optionnel, pour les fonctionnalités avancées)
- 4 GB RAM minimum, 8 GB recommandés
- 20 GB d'espace disque 