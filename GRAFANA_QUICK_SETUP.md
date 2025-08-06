# ⚡ Configuration Rapide Grafana - MCP Daznode

## 🚀 Actions immédiates

### 1. Accès Grafana
```
URL: http://localhost:3000
Login: admin / admin
```

### 2. Ajouter Datasource Prometheus  
```
Configuration > Data Sources > Add > Prometheus
URL: http://localhost:9090 (ou http://prometheus:9090)
```

### 3. Importer les dashboards

**Dashboard Serveur:**
```bash
# Fichier : config/grafana/dashboards/server_monitoring.json
# Import via: Configuration > Dashboards > Import > Upload JSON
```

**Dashboard Daznode:**
```bash  
# Fichier : config/grafana/dashboards/daznode_monitoring.json
# Import via: Configuration > Dashboards > Import > Upload JSON
```

## 📊 Métriques disponibles

### Serveur (api.dazno.de)
- CPU, RAM, Disque : Métriques système temps réel
- API Performance : Requêtes/sec, temps de réponse  
- Infrastructure : Redis, Circuit breakers

### Daznode Lightning
- Capacité : 15.5M sats (12/15 canaux actifs)
- Liquidité : 8.2M local / 7.3M distant (53%/47%)
- Performance : Taux de succès, centralité, revenus
- Alertes : Seuils configurés pour surveillance automatique

## ⚙️ Collecte automatique  

```bash
# Cron installé - collecte toutes les 5 minutes
crontab -l | grep daznode

# Test manuel
./scripts/collect_daznode_metrics.sh

# Métriques générées  
cat /tmp/daznode_metrics.prom
```

## 🎯 Résultat final

**2 dashboards opérationnels :**
1. **Serveur MCP** - Monitoring infrastructure complète
2. **Daznode Lightning** - Métriques réseau Lightning spécialisées

**Surveillance 24/7 :**
- Collecte automatique toutes les 5min
- Alertes Telegram configurées  
- Seuils d'alerte personnalisés
- Historique et tendances

---
✅ **Configuration prête !** Dashboards importables immédiatement dans Grafana.
