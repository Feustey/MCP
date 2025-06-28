# Guide de Déploiement MCP sur Hostinger

## Vue d'ensemble

Ce guide détaille le déploiement de l'application MCP (Moniteur et Contrôleur de Performance) sur Hostinger avec Docker, MongoDB et Redis en ressources locales.

## Prérequis

- Serveur Hostinger avec accès SSH
- Docker et Docker Compose installés
- Domaine `api.dazno.de` configuré et pointant vers le serveur

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Caddy (80/443)│    │   MongoDB       │    │   Redis         │
│   Reverse Proxy │    │   Port: 27017   │    │   Port: 6379    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   MCP API       │
                    │   Port: 8000    │
                    └─────────────────┘
```

## Étapes de Déploiement

### 1. Préparation du Serveur

```bash
# Connexion SSH au serveur Hostinger
ssh user@your-hostinger-server

# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Installation de Docker (si pas déjà installé)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Installation de Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Ajout de l'utilisateur au groupe docker
sudo usermod -aG docker $USER
```

### 2. Clonage du Projet

```bash
# Création du répertoire de travail
mkdir -p /opt/mcp
cd /opt/mcp

# Clonage du repository (si disponible)
git clone https://github.com/Feustey/MCP.git .
# OU téléchargement manuel des fichiers
```

### 3. Configuration des Variables d'Environnement

```bash
# Création du fichier .env
cat > .env << EOF
# Configuration IA
AI_OPENAI_API_KEY=your_openai_api_key_here

# Configuration sécurité
SECURITY_SECRET_KEY=your_secret_key_here

# Configuration Grafana
GRAFANA_PASSWORD=your_grafana_password_here

# Configuration MongoDB (optionnel, valeurs par défaut utilisées)
MONGO_INITDB_ROOT_USERNAME=mcp_admin
MONGO_INITDB_ROOT_PASSWORD=mcp_secure_password_2025

# Configuration Redis (optionnel, valeurs par défaut utilisées)
REDIS_PASSWORD=mcp_redis_password_2025
EOF
```

### 4. Déploiement Automatique

```bash
# Rendre le script exécutable
chmod +x scripts/deploy-hostinger-simple.sh

# Lancement du déploiement
./scripts/deploy-hostinger-simple.sh
```

### 5. Vérification du Déploiement

```bash
# Vérification des conteneurs
docker ps

# Vérification des logs
docker-compose -f docker-compose.hostinger-local.yml logs -f

# Test de l'API
curl http://localhost:8000/health
curl http://api.dazno.de/health
```

## Configuration DNS

Assurez-vous que le domaine `api.dazno.de` pointe vers votre serveur Hostinger :

```
Type: A
Name: api
Value: [IP_DU_SERVEUR_HOSTINGER]
TTL: 300
```

## Endpoints Disponibles

- **API principale** : `https://api.dazno.de`
- **Documentation Swagger** : `https://api.dazno.de/docs`
- **Health check** : `https://api.dazno.de/health`
- **Grafana** : `http://[IP_SERVEUR]:3000` (admin/admin123)
- **Prometheus** : `http://[IP_SERVEUR]:9090`

## Gestion des Services

### Commandes Utiles

```bash
# Voir les logs en temps réel
docker-compose -f docker-compose.hostinger-local.yml logs -f

# Voir les logs d'un service spécifique
docker-compose -f docker-compose.hostinger-local.yml logs -f mcp-api

# Redémarrer un service
docker-compose -f docker-compose.hostinger-local.yml restart mcp-api

# Arrêter tous les services
docker-compose -f docker-compose.hostinger-local.yml down

# Redémarrer tous les services
docker-compose -f docker-compose.hostinger-local.yml up -d

# Mettre à jour l'image
docker pull feustey/dazno:latest
docker-compose -f docker-compose.hostinger-local.yml up -d
```

### Monitoring

```bash
# Vérification de l'utilisation des ressources
docker stats

# Vérification des volumes
docker volume ls

# Vérification des réseaux
docker network ls
```

## Sécurité

### Firewall

```bash
# Ouverture des ports nécessaires
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 3000/tcp  # Grafana (optionnel)
sudo ufw allow 9090/tcp  # Prometheus (optionnel)

# Activation du firewall
sudo ufw enable
```

### Certificats SSL

Les certificats SSL sont automatiquement gérés par Caddy pour le domaine `api.dazno.de`.

## Sauvegarde

### Sauvegarde des Données

```bash
# Sauvegarde MongoDB
docker exec mcp-mongodb mongodump --out /data/backup/$(date +%Y%m%d_%H%M%S)

# Sauvegarde Redis
docker exec mcp-redis redis-cli BGSAVE

# Sauvegarde des volumes
docker run --rm -v mcp_mongodb_data:/data -v $(pwd):/backup alpine tar czf /backup/mongodb_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

### Restauration

```bash
# Restauration MongoDB
docker exec -i mcp-mongodb mongorestore --drop /data/backup/[DATE_BACKUP]

# Restauration des volumes
docker run --rm -v mcp_mongodb_data:/data -v $(pwd):/backup alpine tar xzf /backup/mongodb_backup_[DATE].tar.gz -C /data
```

## Dépannage

### Problèmes Courants

1. **API non accessible**
   ```bash
   # Vérifier les logs
   docker-compose -f docker-compose.hostinger-local.yml logs mcp-api
   
   # Vérifier la connectivité MongoDB
   docker-compose -f docker-compose.hostinger-local.yml exec mongodb mongosh --eval "db.adminCommand('ping')"
   ```

2. **Erreurs de certificat SSL**
   ```bash
   # Vérifier les logs Caddy
   docker-compose -f docker-compose.hostinger-local.yml logs caddy
   
   # Redémarrer Caddy
   docker-compose -f docker-compose.hostinger-local.yml restart caddy
   ```

3. **Problèmes de mémoire**
   ```bash
   # Vérifier l'utilisation mémoire
   docker stats
   
   # Ajuster les limites dans docker-compose.hostinger-local.yml
   ```

### Logs Importants

```bash
# Logs de l'application
docker-compose -f docker-compose.hostinger-local.yml logs -f mcp-api

# Logs de la base de données
docker-compose -f docker-compose.hostinger-local.yml logs -f mongodb

# Logs du reverse proxy
docker-compose -f docker-compose.hostinger-local.yml logs -f caddy
```

## Mise à Jour

### Mise à Jour de l'Application

```bash
# Arrêt des services
docker-compose -f docker-compose.hostinger-local.yml down

# Téléchargement de la nouvelle image
docker pull feustey/dazno:latest

# Redémarrage des services
docker-compose -f docker-compose.hostinger-local.yml up -d

# Vérification
curl http://api.dazno.de/health
```

### Mise à Jour de la Configuration

```bash
# Modification des fichiers de configuration
# Puis redémarrage des services concernés
docker-compose -f docker-compose.hostinger-local.yml restart [service_name]
```

## Support

Pour toute question ou problème :

1. Vérifiez les logs avec `docker-compose logs -f`
2. Consultez la documentation de l'API sur `https://api.dazno.de/docs`
3. Contactez l'équipe de développement

---

**Dernière mise à jour : 7 janvier 2025** 