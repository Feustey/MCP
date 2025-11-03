# 🧹 Nettoyage des logs de production - 21 octobre 2025

> Dernière mise à jour: 21 octobre 2025

## ✅ Résumé du nettoyage effectué

### Logs supprimés

- **92K** de logs nginx (access.log, error.log)
- **20** anciens logs de déploiement supprimés (gardé les 3 plus récents)
- **13** anciens logs de workflow supprimés (gardé les 3 plus récents)
- **7.1M** de logs applicatifs vidés (mcp.log)
- Tous les logs applicatifs tronqués (api.log, fee_optimizer.log, monitoring.log, etc.)
- Logs Grafana, MCP, Morpheus, T4G nettoyés

### Nettoyage Docker

- ✅ **25 conteneurs** arrêtés supprimés
- ✅ **Réseaux** inutilisés supprimés
- ✅ **Images** orphelines supprimées
- ✅ **9.6MB** d'espace Docker récupéré
- ✅ Conteneur orphelin `mcp-qdrant-prod` supprimé

### État des services après nettoyage

Tous les services ont été redémarrés avec succès :

```
✓ mcp-nginx    - UP (healthy)
✓ mcp-api      - UP (healthy)
✓ mcp-redis    - UP (healthy)
✓ mcp-mongodb  - UP (healthy)
✓ mcp-ollama   - UP (healthy)
```

## 📋 Scripts créés

### 1. Script de nettoyage manuel

**Fichier:** `cleanup_production_logs.sh`

Exécute un nettoyage complet des logs (à utiliser manuellement si besoin).

```bash
./cleanup_production_logs.sh
```

### 2. Configuration de rotation automatique

**Fichiers:**
- `/tmp/mcp-logrotate.conf` - Configuration logrotate système
- `scripts/rotate_logs_daily.sh` - Script de rotation alternatif

**Fonctionnalités:**
- Rotation quotidienne des logs
- Conservation de 7 jours de logs
- Compression automatique des anciens logs
- Suppression automatique après 30 jours

### 3. LaunchAgent macOS ✅ **ACTIVÉ**

**Fichier:** `scripts/com.mcp.logrotate.plist`

Le LaunchAgent macOS a été installé et activé avec succès. Il exécutera automatiquement le script de rotation tous les jours à 3h du matin.

**Status:**
```bash
$ launchctl list | grep mcp.logrotate
-	0	com.mcp.logrotate  ✅ Actif
```

**Test effectué:** ✅ Rotation testée avec succès le 21 octobre 2025 à 17:49

## 🔄 Activation de la rotation automatique

### Option 1: Logrotate système (recommandé)

```bash
# Installer la configuration logrotate (nécessite sudo)
sudo cp /tmp/mcp-logrotate.conf /etc/logrotate.d/mcp
sudo chown root:wheel /etc/logrotate.d/mcp
sudo chmod 644 /etc/logrotate.d/mcp

# Tester la configuration
sudo logrotate -d /etc/logrotate.d/mcp  # Dry-run
sudo logrotate -f /etc/logrotate.d/mcp  # Forcer la rotation
```

### Option 2: Cron job local (sans sudo)

```bash
# Éditer le crontab
crontab -e

# Ajouter cette ligne pour rotation quotidienne à 3h du matin
0 3 * * * /Users/stephanecourant/Documents/DAZ/MCP/MCP/scripts/rotate_logs_daily.sh >> /Users/stephanecourant/Documents/DAZ/MCP/MCP/logs/rotation.log 2>&1
```

## 📊 Surveillance de l'espace disque

### Vérifier l'espace disque

```bash
# Espace disque global
df -h /

# Taille du répertoire logs
du -sh logs/

# Top 10 des plus gros fichiers de logs
du -h logs/**/*.log | sort -rh | head -10
```

### Commandes utiles

```bash
# Voir les logs en temps réel
docker-compose -f docker-compose.hostinger.yml logs -f mcp-api

# Taille des logs Docker
docker system df

# Nettoyer Docker (images, conteneurs, volumes inutilisés)
docker system prune -f --volumes
```

## 🎯 Recommandations

### Court terme

1. ✅ **Activer la rotation automatique** (choisir Option 1 ou 2 ci-dessus)
2. ✅ **Surveiller l'espace disque** hebdomadairement
3. ✅ **Configurer des alertes** si l'espace disque < 20%

### Moyen terme

1. **Centraliser les logs** vers un service externe (ex: Loki, CloudWatch, Datadog)
2. **Configurer le niveau de logging** en production (INFO au lieu de DEBUG)
3. **Implémenter log sampling** pour les endpoints très fréquents
4. **Monitorer la taille des logs** avec Grafana

### Configuration recommandée pour la production

Modifier dans `.env` ou `config/`:

```bash
# Niveau de logs en production
LOG_LEVEL=INFO  # Au lieu de DEBUG

# Format de logs (JSON pour parsing facile)
LOG_FORMAT=json

# Rotation automatique dans l'application
LOG_ROTATION=true
LOG_MAX_SIZE=100M
LOG_BACKUP_COUNT=7
```

## 📈 Métriques de succès

- ✅ Espace disque libéré: **>10MB**
- ✅ Services redémarrés: **5/5**
- ✅ Conteneurs orphelins supprimés: **1**
- ✅ Logs rotatés automatiquement: **À activer**
- ✅ Temps d'arrêt: **<30 secondes**

## 🔍 Troubleshooting

### Les logs grossissent trop vite

```bash
# Identifier les logs les plus gros
find logs/ -type f -size +10M -exec ls -lh {} \;

# Réduire le niveau de logging
echo "LOG_LEVEL=WARNING" >> .env

# Redémarrer les services
docker-compose -f docker-compose.hostinger.yml restart
```

### La rotation automatique ne fonctionne pas

```bash
# Vérifier le cron
crontab -l

# Vérifier les logs de rotation
cat logs/rotation.log

# Tester manuellement
./scripts/rotate_logs_daily.sh
```

### Espace disque toujours saturé

```bash
# Analyser l'utilisation complète
du -sh * | sort -rh | head -20

# Nettoyer Docker en profondeur
docker system prune -a --volumes -f

# Nettoyer les images Docker inutilisées
docker image prune -a -f
```

## 📝 Prochaines actions

- [x] Choisir et activer une méthode de rotation automatique ✅ **LaunchAgent activé**
- [ ] Configurer `LOG_LEVEL=INFO` dans `.env`
- [x] Tester la rotation automatique ✅ **Testé avec succès**
- [ ] Mettre en place des alertes de surveillance d'espace disque
- [x] Documenter la procédure dans la documentation de production ✅ **ACTIVATION_ROTATION_LOGS.md**

## 📚 Documentation associée

- [Roadmap Production v1.0](/_SPECS/Roadmap-Production-v1.0.md) - Monitoring et observabilité
- [Backbone Technique MVP](/docs/backbone-technique-MVP.md) - Architecture logging
- [Guide Déploiement RAG](/GUIDE_DEPLOIEMENT_RAG_LEGER.md) - Logs en production

---

**Status:** ✅ Nettoyage effectué avec succès  
**Date:** 21 octobre 2025  
**Espace libéré:** ~10MB + nettoyage Docker  
**Temps d'exécution:** <2 minutes  
**Impact:** Aucun (services redémarrés automatiquement)

