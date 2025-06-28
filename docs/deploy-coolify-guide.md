# Guide de déploiement Docker + Coolify sur Hostinger

> Dernière mise à jour: 27 mai 2025

## Vue d'ensemble

Cette approche utilise Docker en local pour valider l'application, puis Coolify pour déployer sur Hostinger de manière simplifiée.

## Prérequis

- Docker installé localement
- Accès à un serveur Hostinger avec Coolify
- Credentials de base de données Hostinger (MongoDB + Redis)
- Clé API OpenAI

## Étapes de déploiement

### 1. Test rapide local

```bash
# Test de l'image Docker seule
chmod +x scripts/test-docker-coolify.sh
./scripts/test-docker-coolify.sh
```

### 2. Test complet avec services

```bash
# Test avec MongoDB et Redis locaux
docker-compose -f docker-compose.coolify.yml up

# Tester dans un autre terminal
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Arrêter
docker-compose -f docker-compose.coolify.yml down
```

### 3. Préparation pour Coolify

```bash
# Validation et génération des configs
chmod +x scripts/deploy-docker-coolify.sh
./scripts/deploy-docker-coolify.sh
```

### 4. Configuration dans Coolify

#### Option A : Dockerfile (Recommandé)
1. Créer un nouveau projet dans Coolify
2. Connecter votre repository Git
3. Sélectionner `Dockerfile.coolify`
4. Configurer les variables d'environnement (voir section suivante)
5. Déployer

#### Option B : Docker Compose
1. Créer un nouveau projet dans Coolify
2. Sélectionner "Docker Compose"
3. Utiliser le fichier `docker-compose.coolify-deploy.yml` généré
4. Configurer les variables d'environnement
5. Déployer

## Variables d'environnement pour Coolify

### Variables obligatoires

```env
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
DRY_RUN=true
PORT=8000
WORKERS=2

# Base de données Hostinger
MONGO_URL=mongodb://root:VOTRE_PASSWORD@VOTRE_HOST:27017/?directConnection=true
REDIS_HOST=VOTRE_HOST_REDIS
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=VOTRE_PASSWORD_REDIS

# APIs
AI_OPENAI_API_KEY=sk-votre-cle-openai
SECURITY_SECRET_KEY=votre-secret-key-securise
```

### Variables optionnelles

```env
# Sécurité
CORS_ORIGINS=https://api.dazno.de
ALLOWED_HOSTS=api.dazno.de

# Features
ENABLE_METRICS=true
ENABLE_DOCS=true
ENABLE_RAG=false

# Performance
TIMEOUT=30
MAX_REQUESTS=1000
```

## Obtenir les credentials Hostinger

### MongoDB
1. Accédez au panel Hostinger
2. Section "Bases de données" → "MongoDB"
3. Copiez l'URL de connexion complète

### Redis
1. Accédez au panel Hostinger  
2. Section "Bases de données" → "Redis"
3. Notez l'host, port et password

## Configuration du domaine

Dans Coolify, configurez :
- **Domaine** : `api.dazno.de`
- **SSL** : Automatique (Let's Encrypt)
- **Port interne** : `8000`

## Monitoring et maintenance

### Health checks
L'application expose automatiquement :
- `/health` : Status de l'API
- `/metrics` : Métriques Prometheus (si activé)

### Logs
Dans Coolify, surveillez les logs pour :
- Erreurs de connexion aux bases de données
- Erreurs d'authentification API
- Performance et latence

### Rollback
En cas de problème :
1. Coolify permet un rollback en un clic
2. Ou changez `DRY_RUN=true` pour désactiver temporairement

## Troubleshooting

### Erreur 502 Bad Gateway
- Vérifiez que le port 8000 est correctement configuré
- Vérifiez les logs de l'application
- Testez le health check : `/health`

### Erreur de base de données
- Vérifiez les credentials MongoDB/Redis
- Testez la connectivité réseau
- Vérifiez les autorisations IP

### Erreur d'API
- Vérifiez la clé OpenAI
- Vérifiez la clé secrète (32+ caractères)
- Vérifiez les variables d'environnement

## Optimisation production

Une fois en production stable :

1. **Désactiver le mode debug** :
   ```env
   LOG_LEVEL=INFO
   DRY_RUN=false
   ```

2. **Optimiser les ressources** :
   ```env
   WORKERS=4  # Selon CPU disponible
   ```

3. **Activer le monitoring** :
   ```env
   ENABLE_METRICS=true
   ```

## Sécurité

- Utilisez des secrets sécurisés dans Coolify
- Limitez l'accès par IP si nécessaire
- Surveillez les logs de sécurité
- Mettez à jour régulièrement les dépendances

## Avantages de cette approche

✅ **Test local** complet avant déploiement  
✅ **Déploiement simplifié** via Coolify  
✅ **Rollback facile** en cas de problème  
✅ **Monitoring intégré** avec health checks  
✅ **Sécurité** avec utilisateur non-root  
✅ **Fallback automatique** en cas d'erreur  
✅ **SSL automatique** via Coolify  
✅ **Logs centralisés** dans l'interface Coolify  

## Support

En cas de problème :
1. Vérifiez les logs dans Coolify
2. Testez l'endpoint `/health`
3. Vérifiez les variables d'environnement
4. Consultez la documentation des APIs externes 