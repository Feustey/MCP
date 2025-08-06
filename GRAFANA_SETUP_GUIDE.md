# 📊 Guide Configuration Grafana - MCP Lightning Monitoring

## Vue d'ensemble

Ce guide vous permet de configurer Grafana avec des dashboards complets pour :
- **Monitoring serveur** : CPU, RAM, disque, API, Redis
- **Monitoring daznode** : Lightning Network, liquidité, performance

## 🎯 Prérequis

### Services requis
- [x] Prometheus configuré et en fonctionnement
- [x] Grafana installé et accessible
- [x] API MCP avec endpoints `/metrics` actifs
- [x] Collecteur de métriques daznode installé

### Ports et accès
- **Grafana** : http://localhost:3000 (par défaut)
- **Prometheus** : http://localhost:9090
- **API MCP** : https://api.dazno.de

## 📋 Étapes d'installation

### 1. Configuration Prometheus

Vérifiez que Prometheus utilise la configuration fournie :

```bash
# Localisation du fichier de configuration
config/prometheus/prometheus-prod.yml

# Jobs configurés :
- mcp-api (metrics API)
- mongodb (base de données)  
- redis (cache)
- nginx (proxy)
- node (métriques système)
- grafana (monitoring Grafana)
```

### 2. Accès à Grafana

1. Ouvrez votre navigateur : `http://localhost:3000`
2. Connexion par défaut :
   - **Username**: admin
   - **Password**: admin (à changer au premier login)

### 3. Configuration de la datasource Prometheus

#### Option A : Import automatique (recommandé)
1. Placez le fichier `config/grafana/provisioning/datasources/prometheus.yml` dans le dossier de provisioning de Grafana
2. Redémarrez Grafana
3. La datasource sera automatiquement configurée

#### Option B : Configuration manuelle
1. Dans Grafana : **Configuration > Data Sources**
2. Cliquez **Add data source**
3. Sélectionnez **Prometheus**
4. Configuration :
   - **Name**: `prometheus`
   - **URL**: `http://prometheus:9090` (Docker) ou `http://localhost:9090`
   - **Access**: Server (default)
   - **Scrape interval**: 15s
5. Cliquez **Save & Test**

### 4. Import des dashboards

#### Dashboard 1 : Monitoring Serveur

1. **Configuration > Dashboards > Import**
2. Copiez le contenu de `config/grafana/dashboards/server_monitoring.json`
3. Collez dans **Import via panel json**
4. Cliquez **Load**
5. Configurez :
   - **Name**: "Serveur MCP - Monitoring Complet"
   - **Folder**: Créer "MCP Monitoring"
   - **Datasource**: Sélectionner "prometheus"
6. Cliquez **Import**

**Panneaux inclus :**
- CPU Usage (seuils : jaune >70%, rouge >90%)
- Memory Usage (seuils : jaune >80%, rouge >95%)
- Disk Usage (seuils : jaune >85%, rouge >95%)
- API Requests per Second
- Response Time (percentile 95)
- Circuit Breakers Status
- Redis Performance

#### Dashboard 2 : Monitoring Daznode Lightning

1. **Configuration > Dashboards > Import**
2. Copiez le contenu de `config/grafana/dashboards/daznode_monitoring.json`
3. Collez dans **Import via panel json**
4. Cliquez **Load**
5. Configurez :
   - **Name**: "Daznode Lightning - Monitoring ⚡"
   - **Folder**: "MCP Monitoring"
   - **Datasource**: Sélectionner "prometheus"
6. Cliquez **Import**

**Panneaux inclus :**
- Node Info (statut du nœud)
- Total Capacity (15.5M sats)
- Active Channels (12/15)
- Liquidity Balance (graphique en secteurs)
- Revenue Trend (évolution des revenus)
- Channel Performance (tableau détaillé)
- Fee Strategy (stratégie de frais)
- Network Position (score de centralité)
- Success Rate (taux de succès routage)
- Recommendations (actions recommandées)

### 5. Configuration des alertes

#### Règles Prometheus (automatique)
Les règles d'alerting sont configurées dans `config/prometheus/rules/mcp_alerts.yml` :

**Alertes serveur :**
- High CPU Usage (>90% pendant 5min)
- High Memory Usage (>95% pendant 5min)
- Disk Space Low (>90% pendant 10min)
- API High Error Rate (>0.1 erreurs/sec pendant 2min)
- Circuit Breaker Open (immédiat)

**Alertes daznode :**
- Low Liquidity (<20% balance locale pendant 15min)
- High Failure Rate (<85% succès pendant 10min)
- Channel Offline (<10 canaux actifs pendant 5min)

#### Configuration Alertmanager (optionnel)
Pour recevoir les alertes par Telegram/Email, configurez Alertmanager avec le fichier `config/alertmanager/alertmanager.yml`.

### 6. Collecte automatique des métriques daznode

Le collecteur automatique est installé via cron :

```bash
# Vérification de l'installation
crontab -l | grep daznode

# Collecte manuelle (test)
./scripts/collect_daznode_metrics.sh

# Vérification des métriques générées
cat /tmp/daznode_metrics.prom
```

**Métriques collectées :**
- `lightning_node_info` : Informations du nœud
- `lightning_total_capacity_sats` : Capacité totale
- `lightning_active_channels` : Canaux actifs
- `lightning_local_balance_sats` : Balance locale
- `lightning_remote_balance_sats` : Balance distante
- `lightning_routing_success_rate` : Taux de succès
- `lightning_centrality_score` : Score de centralité
- `lightning_fee_rate_ppm` : Taux de frais
- `lightning_routing_revenue_sats` : Revenus de routage
- `lightning_health_score` : Score de santé global

## 🎛️ Utilisation des dashboards

### Dashboard Serveur

**Monitoring en temps réel :**
- Surveillance CPU/RAM/Disque
- Analyse des performances API
- État des circuit breakers
- Métriques Redis et cache

**Seuils configurés :**
- 🟢 Vert : Fonctionnement normal
- 🟡 Jaune : Attention requise
- 🔴 Rouge : Action immédiate nécessaire

### Dashboard Daznode

**Métriques Lightning :**
- Vue d'ensemble du nœud et sa santé
- Balance de liquidité en temps réel
- Performance de routage
- Position dans le réseau

**Recommandations intégrées :**
- Optimisation de liquidité
- Ajustement des frais
- Stratégie d'expansion
- KPI à surveiller

## 🔧 Dépannage

### Dashboard vide ou pas de données

1. **Vérifier Prometheus :**
   ```bash
   curl http://localhost:9090/metrics
   ```

2. **Vérifier les métriques API :**
   ```bash
   curl https://api.dazno.de/metrics
   ```

3. **Vérifier le collecteur daznode :**
   ```bash
   ./scripts/collect_daznode_metrics.sh
   ls -la /tmp/daznode_metrics.prom
   ```

### Datasource non connectée

1. Vérifier l'URL de Prometheus dans Grafana
2. Tester la connexion : **Data Sources > prometheus > Save & Test**
3. Vérifier que Prometheus scrape les targets : `http://localhost:9090/targets`

### Métriques daznode manquantes

1. Vérifier le cron : `crontab -l`
2. Tester manuellement : `./scripts/collect_daznode_metrics.sh`
3. Vérifier les logs : `tail -f /var/log/daznode_metrics.log`

## 📊 Personnalisation

### Modification des seuils

Éditez les dashboards pour ajuster les seuils d'alerte selon vos besoins :
- CPU : 70% (jaune), 90% (rouge)
- Mémoire : 80% (jaune), 95% (rouge)
- Disque : 85% (jaune), 95% (rouge)

### Ajout de métriques

Pour ajouter des métriques personnalisées :
1. Modifiez `scripts/collect_daznode_metrics.sh`
2. Ajoutez les nouvelles métriques au format Prometheus
3. Créez de nouveaux panneaux dans Grafana

### Variables de dashboard

Les dashboards supportent les variables pour :
- **node_id** : ID du nœud Lightning (prédéfini pour daznode)
- **time_range** : Plage de temps (modifiable)
- **refresh** : Intervalle de rafraîchissement

## 🚀 Maintenance

### Nettoyage automatique

- Logs daznode : Nettoyage hebdomadaire (dimanche 2h00)
- Métriques anciennes : Rotation automatique
- Cache Redis : Surveillance intégrée

### Sauvegarde des dashboards

Exportez régulièrement vos dashboards :
1. **Dashboard Settings > JSON Model**
2. Copiez le JSON
3. Sauvegardez dans le contrôle de version

## 📞 Support

En cas de problème :
1. Consultez les logs : `/var/log/daznode_metrics.log`
2. Vérifiez les services : Prometheus, Grafana, API MCP
3. Testez les endpoints manuellement
4. Contactez l'équipe technique via Telegram

---

**✅ Configuration terminée !**

Vos dashboards Grafana sont maintenant opérationnels avec :
- 📈 Monitoring serveur complet
- ⚡ Surveillance Lightning daznode  
- 🚨 Alertes automatiques
- 📊 Métriques temps réel

**Accès rapide :**
- Grafana : http://localhost:3000
- Prometheus : http://localhost:9090  
- API Métriques : https://api.dazno.de/metrics
