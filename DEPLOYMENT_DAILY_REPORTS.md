# 🚀 Guide de Déploiement : Rapports Quotidiens

> **Version** : 1.0.0  
> **Date** : 5 novembre 2025  
> **Status** : Production Ready

---

## ✅ Checklist pré-déploiement

### 1. Vérifications préliminaires

- [ ] **Code review** : Tous les fichiers ont été reviewés
- [ ] **Tests** : Coverage > 85% sur les modules critiques
- [ ] **Linting** : Aucune erreur (vérifié avec flake8/pylint)
- [ ] **Documentation** : Complète et à jour
- [ ] **Dépendances** : `requirements-production.txt` mis à jour avec APScheduler

### 2. Infrastructure

- [ ] **MongoDB** : Version 6.0+ avec replica set recommandé
- [ ] **Redis** : Version 7.0+ (optionnel mais recommandé)
- [ ] **Serveur** : Min 2 vCPU, 4GB RAM (recommandé: 4 vCPU, 8GB RAM)
- [ ] **Stockage** : Min 50GB SSD (pour assets RAG)
- [ ] **Réseau** : Accès APIs externes (Amboss, Mempool)

### 3. Configuration

- [ ] **Variables d'environnement** : `.env` configuré
- [ ] **Collections MongoDB** : Index créés
- [ ] **Répertoires** : `rag/RAG_assets/reports/daily/` créé
- [ ] **Permissions** : Write access sur répertoire RAG

---

## 📋 Étapes de déploiement

### Étape 1 : Backup

```bash
# Backup MongoDB
mongodump --uri="mongodb://localhost:27017/mcp_db" --out=/backup/mcp_pre_daily_reports_$(date +%Y%m%d)

# Backup code actuel
cd /var/www/mcp
tar -czf /backup/mcp_code_$(date +%Y%m%d).tar.gz .
```

### Étape 2 : Installation des dépendances

```bash
# Activer virtualenv
source venv/bin/activate

# Installer APScheduler
pip install APScheduler>=3.10.0,<4.0.0

# Ou installer toutes les dépendances mises à jour
pip install -r requirements-production.txt --upgrade
```

### Étape 3 : Configuration des variables d'environnement

Ajouter à `/etc/mcp/.env` ou `.env` :

```bash
# === Daily Reports Configuration ===
DAILY_REPORTS_SCHEDULER_ENABLED=true
DAILY_REPORTS_HOUR=6
DAILY_REPORTS_MINUTE=0
DAILY_REPORTS_MAX_CONCURRENT=10
DAILY_REPORTS_MAX_RETRIES=3
DAILY_REPORTS_TIMEOUT=300
```

### Étape 4 : Création des répertoires

```bash
# Créer structure pour assets RAG
mkdir -p rag/RAG_assets/reports/daily
chmod 755 rag/RAG_assets/reports/daily

# Vérifier permissions
ls -la rag/RAG_assets/reports/
```

### Étape 5 : Création des index MongoDB

```bash
# Connexion à MongoDB
mongosh mongodb://localhost:27017/mcp_db

# Créer index sur user_profiles
db.user_profiles.createIndex({ "lightning_pubkey": 1 }, { unique: true, sparse: true })
db.user_profiles.createIndex({ "daily_report_enabled": 1 })
db.user_profiles.createIndex({ "tenant_id": 1, "lightning_pubkey": 1 })

# Créer index sur daily_reports
db.daily_reports.createIndex({ "report_id": 1 }, { unique: true })
db.daily_reports.createIndex({ "user_id": 1, "report_date": -1 })
db.daily_reports.createIndex({ "node_pubkey": 1, "report_date": -1 })
db.daily_reports.createIndex({ "tenant_id": 1, "report_date": -1 })
db.daily_reports.createIndex({ "generation_status": 1 })

# TTL index pour auto-suppression après 90 jours
db.daily_reports.createIndex(
  { "report_date": 1 },
  { expireAfterSeconds: 7776000 }  // 90 jours
)

# Vérifier les index
db.user_profiles.getIndexes()
db.daily_reports.getIndexes()
```

### Étape 6 : Déploiement du code

```bash
# Arrêter l'application
sudo systemctl stop mcp-api

# Pull dernières modifications (ou copier fichiers)
git pull origin main

# Ou copier les nouveaux fichiers
cp -r /tmp/daily_reports_update/* /var/www/mcp/

# Vérifier que tous les fichiers sont présents
ls -la config/models/daily_reports.py
ls -la app/routes/daily_reports.py
ls -la app/services/daily_report_generator.py
ls -la app/scheduler/daily_report_scheduler.py
```

### Étape 7 : Tests pré-production

```bash
# Activer virtualenv
source venv/bin/activate

# Lancer tests unitaires
pytest tests/test_daily_reports.py -v

# Vérifier imports
python -c "from config.models.daily_reports import DailyReport; print('OK')"
python -c "from app.routes.daily_reports import router; print('OK')"
python -c "from app.services.daily_report_generator import DailyReportGenerator; print('OK')"
python -c "from app.scheduler.daily_report_scheduler import DailyReportScheduler; print('OK')"

# Test import APScheduler
python -c "from apscheduler.schedulers.asyncio import AsyncIOScheduler; print('APScheduler OK')"
```

### Étape 8 : Démarrage de l'application

```bash
# Démarrer l'application
sudo systemctl start mcp-api

# Vérifier que l'app démarre correctement
sudo systemctl status mcp-api

# Vérifier les logs de démarrage
sudo journalctl -u mcp-api -f --since "1 minute ago"
```

### Étape 9 : Vérification du scheduler

```bash
# Chercher dans les logs que le scheduler a démarré
sudo tail -f /var/log/mcp/app.log | grep -i "scheduler"

# Attendu dans les logs:
# "Daily report scheduler started - will run daily at 06:00 UTC"
```

### Étape 10 : Test fonctionnel

#### A. Test activation workflow

```bash
# Obtenir un JWT token de test
export JWT_TOKEN="your_test_user_jwt_token"

# Activer les rapports quotidiens
curl -X POST https://api.dazno.de/api/v1/user/profile/daily-report/enable \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json"

# Vérifier le statut
curl -X GET https://api.dazno.de/api/v1/user/profile/daily-report/status \
  -H "Authorization: Bearer $JWT_TOKEN"
```

#### B. Test génération manuelle (Admin)

```bash
# Obtenir un JWT token admin
export ADMIN_TOKEN="your_admin_jwt_token"

# Déclencher génération manuelle pour un user de test
curl -X POST https://api.dazno.de/api/v1/admin/reports/daily/trigger \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_ids": ["test_user_id"]}'

# Surveiller les logs
sudo tail -f /var/log/mcp/app.log | grep "daily_report"

# Attendre la fin de génération (15-30 secondes)
# Chercher: "Report {report_id} generated successfully"
```

#### C. Test consultation rapport

```bash
# Récupérer le dernier rapport
curl -X GET https://api.dazno.de/api/v1/reports/daily/latest \
  -H "Authorization: Bearer $JWT_TOKEN" | jq '.report.summary'

# Vérifier l'historique
curl -X GET "https://api.dazno.de/api/v1/reports/daily/history?days=7" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq '.reports | length'
```

#### D. Vérifier stockage RAG

```bash
# Vérifier que le fichier JSON a été créé
ls -la rag/RAG_assets/reports/daily/test_user_id/

# Vérifier le contenu
cat rag/RAG_assets/reports/daily/test_user_id/$(date +%Y%m%d).json | jq '.summary'
```

---

## 📊 Monitoring post-déploiement

### 1. Vérifications immédiates (J+0)

```bash
# Vérifier que l'app tourne
systemctl status mcp-api

# Vérifier logs d'erreurs
sudo grep ERROR /var/log/mcp/app.log | tail -20

# Vérifier métriques
curl -s http://localhost:8000/metrics | grep daily_reports

# Vérifier connexions DB
mongosh --eval "db.serverStatus().connections"
```

### 2. Surveillance J+1 (Après premier batch)

Le lendemain matin après 06:00 UTC :

```bash
# Vérifier que le scheduler a tourné
sudo grep "Starting scheduled daily reports generation" /var/log/mcp/app.log

# Vérifier nombre de rapports générés
mongosh mcp_db --eval "db.daily_reports.countDocuments({
  generation_timestamp: { \$gte: new Date(Date.now() - 86400000) }
})"

# Vérifier taux de succès
mongosh mcp_db --eval "
var total = db.daily_reports.countDocuments({generation_timestamp: { \$gte: new Date(Date.now() - 86400000) }});
var failed = db.daily_reports.countDocuments({generation_timestamp: { \$gte: new Date(Date.now() - 86400000) }, generation_status: 'failed'});
print('Total: ' + total + ', Failed: ' + failed + ', Success rate: ' + ((total-failed)/total*100).toFixed(2) + '%');
"

# Obtenir statistiques via API admin
curl -X GET https://api.dazno.de/api/v1/admin/reports/daily/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.stats'
```

### 3. Dashboard Grafana

Créer un dashboard avec les métriques suivantes :

```promql
# Taux de rapports générés
rate(daily_reports_generated_total[1h])

# Durée moyenne de génération
histogram_quantile(0.95, daily_reports_generation_duration_seconds_bucket)

# Taux d'erreur
rate(daily_reports_errors_total[1h])

# Nombre d'utilisateurs actifs
daily_reports_users_enabled_total
```

### 4. Alertes Slack/Email

Configurer des alertes pour :

- ✅ Scheduler n'a pas tourné à 06:00 UTC
- ✅ Taux d'erreur > 5%
- ✅ Durée de génération > 60s (p95)
- ✅ Aucun rapport généré depuis 25h

---

## 🔥 Rollback d'urgence

### Si problème critique détecté

```bash
# 1. Désactiver le scheduler immédiatement
# Éditer /etc/mcp/.env
DAILY_REPORTS_SCHEDULER_ENABLED=false

# 2. Redémarrer l'application
sudo systemctl restart mcp-api

# 3. Restaurer backup code
cd /var/www/mcp
sudo systemctl stop mcp-api
tar -xzf /backup/mcp_code_YYYYMMDD.tar.gz
sudo systemctl start mcp-api

# 4. Restaurer backup MongoDB (si nécessaire)
mongorestore --uri="mongodb://localhost:27017/mcp_db" \
  --drop \
  /backup/mcp_pre_daily_reports_YYYYMMDD/mcp_db/

# 5. Notifier équipe
# Envoyer message sur Slack #incidents
```

### Rollback partiel (désactiver uniquement le scheduler)

Si l'API fonctionne mais le scheduler pose problème :

```bash
# Désactiver le scheduler sans tout rollback
echo "DAILY_REPORTS_SCHEDULER_ENABLED=false" >> /etc/mcp/.env

# Redémarrer
sudo systemctl restart mcp-api

# Les endpoints API resteront fonctionnels
# Seule la génération automatique sera désactivée
```

---

## 📈 Optimisations post-déploiement

### Semaine 1-2 : Monitoring et tuning

#### A. Analyser les performances

```bash
# Durée moyenne de génération
grep "generation_duration" /var/log/mcp/app.log | \
  awk '{sum+=$NF; count++} END {print "Average:", sum/count, "seconds"}'

# Identifier les rapports lents
grep "generation_duration" /var/log/mcp/app.log | \
  awk '$NF > 30' | tail -10
```

#### B. Ajuster la concurrence

Si génération trop lente :

```bash
# Augmenter le nombre de rapports parallèles
# Dans .env
DAILY_REPORTS_MAX_CONCURRENT=20  # Au lieu de 10

# Redémarrer
sudo systemctl restart mcp-api
```

#### C. Optimiser les requêtes MongoDB

```bash
# Analyser les requêtes lentes
mongosh mcp_db --eval "
db.setProfilingLevel(2);  // Log toutes les requêtes
"

# Après 24h, vérifier les requêtes lentes
mongosh mcp_db --eval "
db.system.profile.find({millis: {\$gt: 100}}).sort({millis: -1}).limit(10);
"
```

### Mois 1 : Optimisations avancées

1. **Cache Redis** : Activer cache pour embeddings RAG
2. **Batch processing** : Traiter par batch de 50 users
3. **Queue system** : Implémenter Celery pour better scalability
4. **CDN** : Pour assets statiques (export PDF)

---

## 🎯 KPIs de succès

### Objectifs Semaine 1

| Métrique | Objectif | Critique |
|----------|----------|----------|
| Taux de succès génération | > 95% | > 90% |
| Durée moyenne génération | < 25s | < 40s |
| Uptime API | > 99.5% | > 99% |
| Erreurs critiques | 0 | < 5 |

### Objectifs Mois 1

| Métrique | Objectif |
|----------|----------|
| Utilisateurs actifs (workflow enabled) | > 100 |
| Rapports générés/jour | > 100 |
| Satisfaction utilisateurs (NPS) | > 80% |
| Taux d'adoption | > 30% des users avec pubkey |

---

## 📞 Support post-déploiement

### Équipe d'astreinte

- **Lead Dev** : Disponible H24 J+0 à J+7
- **DevOps** : Disponible pour escalade infrastructure
- **Product Owner** : Point de contact utilisateurs

### Procédure d'escalade

1. **Incident mineur** : Log dans #tech-issues, correction J+1
2. **Incident majeur** : Alert dans #incidents, correction < 4h
3. **Incident critique** : Call d'astreinte, rollback immédiat

### Contacts

- **Slack** : #daily-reports-support
- **PagerDuty** : Escalade automatique si erreurs critiques
- **Email** : tech-support@dazno.de

---

## ✅ Validation finale

### Checklist de validation

- [ ] Application démarrée sans erreur
- [ ] Scheduler actif et schedulé correctement
- [ ] Test activation workflow réussi
- [ ] Test génération manuelle réussi
- [ ] Rapport consultable via API
- [ ] Stockage RAG fonctionnel
- [ ] Index MongoDB créés
- [ ] Monitoring configuré
- [ ] Alertes configurées
- [ ] Documentation à jour
- [ ] Équipe formée
- [ ] Plan de rollback validé

### Sign-off

| Rôle | Nom | Signature | Date |
|------|-----|-----------|------|
| Lead Dev | ___________ | _________ | ___/___/___ |
| DevOps | ___________ | _________ | ___/___/___ |
| Product Owner | ___________ | _________ | ___/___/___ |
| QA Lead | ___________ | _________ | ___/___/___ |

---

## 📝 Post-mortem (À remplir après J+7)

### Ce qui a bien fonctionné
- 
- 
- 

### Problèmes rencontrés
- 
- 
- 

### Améliorations pour prochains déploiements
- 
- 
- 

---

**Version** : 1.0.0  
**Date création** : 5 novembre 2025  
**Auteur** : MCP Team

