# 📋 Deployment Runbook - MCP

> Procédures opérationnelles pour le déploiement et la gestion de MCP en production

## 🎯 Vue d'ensemble

Ce runbook contient les procédures standardisées pour gérer MCP en production, incluant les déploiements, rollbacks, incidents, et maintenance.

## 🚀 Déploiement standard

### Déploiement automatique (recommandé)

```bash
# 1. Créer une branche feature
git checkout -b feature/ma-fonctionnalite

# 2. Développer et tester localement
# ... modifications ...

# 3. Commit et push
git add .
git commit -m "feat: description de la fonctionnalité"
git push origin feature/ma-fonctionnalite

# 4. Créer une Pull Request sur GitHub
# Review → Approve → Merge to main

# 5. Le CI/CD se déclenche automatiquement
# Suivre dans l'onglet Actions sur GitHub
```

**Durée estimée:** 10-12 minutes

### Déploiement manuel d'urgence

Si le CI/CD n'est pas disponible :

```bash
# Se connecter au serveur
ssh feustey@147.79.101.32

# Aller dans le répertoire
cd /opt/mcp

# Créer un backup
sudo tar czf /opt/mcp-backups/manual-backup-$(date +%Y%m%d_%H%M%S).tar.gz \
  docker-compose.production.yml \
  .env.production \
  mcp-data/

# Pull les dernières modifications
git pull origin main

# Rebuild et redémarrer
sudo docker-compose -f docker-compose.production.yml build --no-cache
sudo docker-compose -f docker-compose.production.yml up -d

# Attendre 60 secondes
sleep 60

# Vérifier la santé
curl http://localhost:8000/api/v1/health

# Voir les logs
sudo docker-compose -f docker-compose.production.yml logs -f
```

**Durée estimée:** 15-20 minutes

## ⏪ Rollback

### Rollback automatique (via GitHub Actions)

```bash
# 1. Aller sur GitHub Actions
# 2. Sélectionner "Rollback Production"
# 3. Run workflow
# 4. Entrer "latest" ou un timestamp spécifique
# 5. Confirmer
```

**Durée estimée:** 2-3 minutes

### Rollback manuel

```bash
# Se connecter au serveur
ssh feustey@147.79.101.32

# Lister les backups disponibles
ls -lh /opt/mcp-backups/

# Choisir un backup (le plus récent généralement)
BACKUP_FILE=$(ls -t /opt/mcp-backups/mcp-backup-*.tar.gz | head -1)

# Arrêter les services
cd /opt/mcp
sudo docker-compose -f docker-compose.production.yml down

# Restaurer le backup
sudo tar xzf "$BACKUP_FILE" -C /opt/mcp

# Redémarrer les services
sudo docker-compose -f docker-compose.production.yml up -d

# Attendre et vérifier
sleep 60
curl http://localhost:8000/api/v1/health
```

**Durée estimée:** 3-5 minutes

## 🏥 Health Checks

### Vérification rapide

```bash
# Health endpoint
curl https://api.dazno.de/api/v1/health

# Réponse attendue: HTTP 200
# {"status": "healthy", "timestamp": "..."}
```

### Vérification complète

```bash
# Se connecter au serveur
ssh feustey@147.79.101.32
cd /opt/mcp

# Status des containers
sudo docker-compose -f docker-compose.production.yml ps

# Tous devraient être "Up (healthy)"

# Vérifier l'API
curl http://localhost:8000/api/v1/health

# Vérifier MongoDB
sudo docker exec mcp-mongodb-prod mongosh --eval "db.adminCommand('ping')"

# Vérifier Redis
sudo docker exec mcp-redis-prod redis-cli ping

# Vérifier Qdrant
sudo docker exec mcp-qdrant-prod curl -sf http://localhost:6333/health

# Vérifier Ollama
sudo docker exec mcp-ollama wget -q --spider http://localhost:11434/api/tags
```

### Vérification des ressources

```bash
# Utilisation CPU/Mémoire
sudo docker stats --no-stream

# Espace disque
df -h /opt/mcp
df -h /opt/mcp-backups

# Logs récents (vérifier absence d'erreurs)
sudo docker-compose -f docker-compose.production.yml logs --tail=100 | grep -i error
```

## 🚨 Gestion d'incidents

### Incident Niveau 1 (Critique) - Service Down

**Symptômes:** API ne répond pas, containers arrêtés

**Procédure:**

```bash
# 1. Vérifier l'état
ssh feustey@147.79.101.32
cd /opt/mcp
sudo docker-compose -f docker-compose.production.yml ps

# 2. Voir les logs
sudo docker-compose -f docker-compose.production.yml logs --tail=100

# 3. Si containers arrêtés, redémarrer
sudo docker-compose -f docker-compose.production.yml up -d

# 4. Si échec, rollback immédiat
BACKUP_FILE=$(ls -t /opt/mcp-backups/mcp-backup-*.tar.gz | head -1)
sudo docker-compose -f docker-compose.production.yml down
sudo tar xzf "$BACKUP_FILE" -C /opt/mcp
sudo docker-compose -f docker-compose.production.yml up -d

# 5. Notifier l'équipe
# 6. Analyser les logs pour la cause racine
```

**SLA:** < 5 minutes de résolution

### Incident Niveau 2 (Majeur) - Performance dégradée

**Symptômes:** API lente, timeouts, erreurs 5xx sporadiques

**Procédure:**

```bash
# 1. Vérifier les ressources
sudo docker stats --no-stream

# 2. Vérifier les logs
sudo docker-compose -f docker-compose.production.yml logs --tail=200 | grep -E "error|timeout|exception"

# 3. Redémarrer les services si nécessaire
sudo docker-compose -f docker-compose.production.yml restart

# 4. Surveiller l'amélioration
watch -n 5 'curl -w "\nTime: %{time_total}s\n" https://api.dazno.de/api/v1/health'

# 5. Si pas d'amélioration, rollback
```

**SLA:** < 15 minutes de résolution

### Incident Niveau 3 (Mineur) - Fonctionnalité dégradée

**Symptômes:** Une fonctionnalité spécifique ne fonctionne pas correctement

**Procédure:**

```bash
# 1. Identifier la fonctionnalité
# 2. Vérifier les logs spécifiques
sudo docker-compose -f docker-compose.production.yml logs -f mcp-api-prod | grep "fonction_concernee"

# 3. Si critique, activer le mode Shadow/Dry-Run
ssh feustey@147.79.101.32
cd /opt/mcp
nano .env.production
# Mettre DRY_RUN=true
sudo docker-compose -f docker-compose.production.yml restart

# 4. Planifier un fix et redéploiement
```

**SLA:** < 1 heure d'acknowledgment, fix dans les 24h

## 🔧 Maintenance

### Maintenance programmée

**Notification:** Prévenir 48h à l'avance

```bash
# 1. Créer un backup complet
ssh feustey@147.79.101.32
cd /opt/mcp
sudo tar czf /opt/mcp-backups/maintenance-backup-$(date +%Y%m%d).tar.gz \
  docker-compose.production.yml \
  .env.production \
  mcp-data/ \
  config/

# 2. Mettre en mode maintenance (optionnel)
# Créer un fichier nginx de maintenance

# 3. Effectuer la maintenance
# ... opérations ...

# 4. Tester
curl http://localhost:8000/api/v1/health

# 5. Retirer le mode maintenance
# 6. Surveiller pendant 30 minutes
```

### Mise à jour des dépendances

```bash
# Sur une branche dédiée
git checkout -b update/dependencies

# Mettre à jour requirements
pip list --outdated
# Mettre à jour requirements-production.txt

# Tester localement
pip install -r requirements-production.txt
pytest tests/

# Commit et push
git commit -m "chore: update dependencies"
git push origin update/dependencies

# PR → Review → Merge
# CI/CD se charge du déploiement
```

### Rotation des secrets

```bash
# 1. Générer de nouveaux secrets
openssl rand -base64 32

# 2. Mettre à jour .env.production sur le serveur
ssh feustey@147.79.101.32
cd /opt/mcp
nano .env.production
# Modifier les secrets nécessaires

# 3. Redémarrer les services
sudo docker-compose -f docker-compose.production.yml restart

# 4. Vérifier
curl http://localhost:8000/api/v1/health

# 5. Mettre à jour les secrets GitHub si nécessaire
```

### Nettoyage des backups

```bash
# Automatique via le CI/CD (garde les 5 derniers)
# Ou manuel :

ssh feustey@147.79.101.32

# Lister les backups
ls -lh /opt/mcp-backups/

# Supprimer les backups de plus de 30 jours
find /opt/mcp-backups/ -name "mcp-backup-*.tar.gz" -mtime +30 -delete

# Vérifier l'espace libéré
df -h /opt/mcp-backups
```

### Nettoyage Docker

```bash
ssh feustey@147.79.101.32

# Images non utilisées
sudo docker image prune -af --filter "until=72h"

# Containers arrêtés
sudo docker container prune -f

# Volumes non utilisés
sudo docker volume prune -f

# Networks non utilisés
sudo docker network prune -f

# Vérifier l'espace libéré
df -h
```

## 📊 Monitoring

### Métriques à surveiller

- **Uptime API:** > 99.5%
- **Response time (p95):** < 500ms
- **Error rate:** < 0.5%
- **CPU usage:** < 70%
- **Memory usage:** < 80%
- **Disk usage:** < 85%
- **Container health:** All healthy

### Alertes configurées

| Alerte | Seuil | Action |
|--------|-------|--------|
| API Down | 2 échecs consécutifs | Page immédiate |
| Response time élevé | > 1s sur 5min | Investigation |
| Error rate élevé | > 2% | Investigation |
| Disk > 90% | - | Nettoyage urgent |
| Memory > 90% | - | Redémarrage planifié |

## 📝 Logs

### Accéder aux logs

```bash
# Logs en temps réel
ssh feustey@147.79.101.32
cd /opt/mcp
sudo docker-compose -f docker-compose.production.yml logs -f

# Logs d'un service spécifique
sudo docker-compose -f docker-compose.production.yml logs -f mcp-api-prod

# Logs avec recherche
sudo docker-compose -f docker-compose.production.yml logs --tail=1000 | grep -i "error"

# Sauvegarder les logs pour analyse
sudo docker-compose -f docker-compose.production.yml logs --tail=5000 > /tmp/mcp-logs-$(date +%Y%m%d).txt
```

### Niveaux de logs

- **DEBUG:** Informations détaillées de débogage
- **INFO:** Opérations normales
- **WARNING:** Situations anormales mais gérables
- **ERROR:** Erreurs nécessitant attention
- **CRITICAL:** Erreurs critiques nécessitant intervention immédiate

## 🔐 Sécurité

### Audit de sécurité

```bash
# Vérifier les ports ouverts
sudo netstat -tlnp

# Vérifier les connexions actives
sudo docker exec mcp-api-prod netstat -an | grep ESTABLISHED

# Vérifier les logs d'accès nginx
sudo docker exec mcp-nginx-prod cat /var/log/nginx/access.log | tail -100

# Vérifier les tentatives d'accès suspectes
sudo grep "Failed" /var/log/auth.log | tail -50
```

### Mise à jour de sécurité urgente

```bash
# 1. Évaluer la criticité (CVSS score)
# 2. Si critique (CVSS > 7), intervention immédiate

# 3. Créer un hotfix
git checkout -b hotfix/security-CVE-XXXX

# 4. Appliquer le patch
# ... modifications ...

# 5. Tests rapides
pytest tests/ -k security

# 6. Déploiement accéléré
git commit -m "fix: security patch CVE-XXXX"
git push origin hotfix/security-CVE-XXXX

# PR → Fast-track review → Merge
# CI/CD déploie automatiquement

# 7. Vérification post-patch
```

## 📞 Contacts

### Escalade

1. **Niveau 1:** DevOps on-call
2. **Niveau 2:** Lead Developer
3. **Niveau 3:** CTO

### Outils

- **Monitoring:** GitHub Actions, Docker
- **Communication:** Slack, Email
- **Documentation:** GitHub Wiki, README

## 📚 Références

- [Documentation CI/CD complète](./CICD_SETUP.md)
- [Quickstart CI/CD](../CICD_QUICKSTART.md)
- [Architecture MCP](./backbone-technique-MVP.md)
- [Roadmap Production](../_SPECS/Roadmap-Production-v1.0.md)

---

**Dernière mise à jour:** 17 octobre 2025  
**Prochaine revue:** Mensuelle  
**Maintenu par:** DevOps Team

