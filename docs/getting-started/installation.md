# Installation

Ce guide vous aidera à installer et configurer MCP sur votre système.

## Prérequis

### Système
- Linux, macOS ou Windows
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- git

### Services
- MongoDB 4.4+
- Redis 6.0+
- Compte OpenAI (pour l'API)

## Installation

### 1. Cloner le Repository

```bash
git clone https://github.com/dazno/mcp.git
cd mcp
```

### 2. Créer un Environnement Virtuel

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
.\venv\Scripts\activate  # Windows
```

### 3. Installer les Dépendances

```bash
pip install -r requirements.txt
```

### 4. Configuration

Créez un fichier `.env` à la racine du projet :

```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=mcp

# Redis
REDIS_URL=redis://localhost:6379

# OpenAI
OPENAI_API_KEY=votre_clé_api

# LNBits (optionnel)
LNBITS_API_URL=https://votre-instance.lnbits.com
LNBITS_ADMIN_KEY=votre_clé_admin
LNBITS_INVOICE_KEY=votre_clé_invoice
```

### 5. Initialisation de la Base de Données

```bash
python src/init_db.py
```

### 6. Vérification de l'Installation

```bash
python src/test_installation.py
```

## Configuration Avancée

### MongoDB

```yaml
# Configuration recommandée pour MongoDB
storage:
  engine: wiredTiger
  journal:
    enabled: true
  dbPath: /data/db
  wiredTiger:
    engineConfig:
      cacheSizeGB: 1
```

### Redis

```conf
# Configuration recommandée pour Redis
maxmemory 1gb
maxmemory-policy allkeys-lru
appendonly yes
```

### Optimisation des Performances

```python
# Dans config.py
CACHE_TTL = 3600  # Durée de vie du cache en secondes
BATCH_SIZE = 100  # Taille des lots pour le traitement
MAX_CONNECTIONS = 10  # Nombre maximum de connexions simultanées
```

## Dépannage

### Problèmes Courants

1. **Erreur de Connexion MongoDB**
   - Vérifiez que MongoDB est en cours d'exécution
   - Vérifiez les identifiants dans `.env`

2. **Erreur Redis**
   - Vérifiez que Redis est en cours d'exécution
   - Vérifiez l'URL Redis dans `.env`

3. **Erreur OpenAI**
   - Vérifiez que votre clé API est valide
   - Vérifiez votre quota d'API

### Logs

Les logs sont stockés dans le dossier `logs/` :
- `mcp.log` : Logs principaux
- `error.log` : Logs d'erreur
- `access.log` : Logs d'accès

## Mise à Jour

Pour mettre à jour MCP :

```bash
git pull
pip install -r requirements.txt
python src/update_db.py
```

## Support

Pour toute question ou problème :
- Issues GitHub : [github.com/dazno/mcp/issues](https://github.com/dazno/mcp/issues)
- Email : support@dazno.de 