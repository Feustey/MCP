# 🔄 Activation de la rotation automatique des logs

> Date: 21 octobre 2025

## ⚠️ Permissions requises

Sur macOS, le Terminal/Cursor nécessite des permissions spéciales pour modifier le crontab. Voici 3 méthodes pour activer la rotation automatique.

## 📋 Méthode 1: Crontab manuel (RECOMMANDÉ)

### Étape 1: Ouvrir le Terminal natif macOS

1. Ouvrir **Terminal.app** (Applications → Utilitaires → Terminal)
2. Naviguer vers le projet:

```bash
cd /Users/stephanecourant/Documents/DAZ/MCP/MCP
```

### Étape 2: Éditer le crontab

```bash
crontab -e
```

### Étape 3: Ajouter cette ligne à la fin du fichier

```bash
# Rotation automatique des logs MCP tous les jours à 3h du matin
0 3 * * * /Users/stephanecourant/Documents/DAZ/MCP/MCP/scripts/rotate_logs_daily.sh >> /Users/stephanecourant/Documents/DAZ/MCP/MCP/logs/rotation.log 2>&1
```

### Étape 4: Sauvegarder et quitter

- Appuyer sur `ESC`
- Taper `:wq` puis `ENTER` (si vim)
- Ou `Ctrl+X`, puis `Y`, puis `ENTER` (si nano)

### Étape 5: Vérifier l'installation

```bash
crontab -l | grep rotate_logs_daily
```

Vous devriez voir la ligne ajoutée.

---

## 📋 Méthode 2: LaunchAgent macOS (ALTERNATIVE)

Si le crontab ne fonctionne pas, utilisez le système natif macOS **launchd**.

### Créer le fichier LaunchAgent

Le fichier a déjà été préparé: `scripts/com.mcp.logrotate.plist`

```bash
# Copier vers le dossier LaunchAgents
cp scripts/com.mcp.logrotate.plist ~/Library/LaunchAgents/

# Charger le service
launchctl load ~/Library/LaunchAgents/com.mcp.logrotate.plist

# Vérifier qu'il est actif
launchctl list | grep mcp.logrotate
```

### Commandes utiles LaunchAgent

```bash
# Démarrer maintenant (test)
launchctl start com.mcp.logrotate

# Arrêter
launchctl stop com.mcp.logrotate

# Décharger (désactiver)
launchctl unload ~/Library/LaunchAgents/com.mcp.logrotate.plist

# Recharger (après modification)
launchctl unload ~/Library/LaunchAgents/com.mcp.logrotate.plist
launchctl load ~/Library/LaunchAgents/com.mcp.logrotate.plist
```

---

## 📋 Méthode 3: Script manuel hebdomadaire

Si vous préférez un contrôle manuel, exécutez simplement le script quand vous voulez:

```bash
cd /Users/stephanecourant/Documents/DAZ/MCP/MCP
./scripts/rotate_logs_daily.sh
```

**Recommandation:** Exécuter une fois par semaine le lundi matin.

---

## ✅ Vérification que ça fonctionne

### Test immédiat du script

```bash
cd /Users/stephanecourant/Documents/DAZ/MCP/MCP
./scripts/rotate_logs_daily.sh

# Vérifier le log de rotation
cat logs/rotation.log
```

### Vérifier après 24h (si cron/launchd actif)

```bash
# Le fichier rotation.log devrait avoir une entrée quotidienne
tail -20 logs/rotation.log

# Les vieux logs devraient être compressés
ls -lh logs/*.gz
```

---

## 🎯 Configuration choisie

**Status actuel:** ⏸️ En attente d'activation manuelle

**Configuration préparée:**
- ✅ Script de rotation créé: `scripts/rotate_logs_daily.sh`
- ✅ Configuration prête: `/tmp/current_crontab`
- ⏸️ **À faire:** Choisir et activer une méthode (1, 2 ou 3)

---

## 📊 Que fait le script de rotation ?

Le script `rotate_logs_daily.sh` effectue automatiquement:

1. **Compression** des logs de plus de 7 jours (`.log` → `.log.gz`)
2. **Suppression** des archives de plus de 30 jours (`.log.gz`)
3. **Troncature** des logs actuels trop gros (>100MB → 50MB)
4. **Nettoyage** des vieux logs de déploiement (garde les 10 plus récents)
5. **Log** de l'opération dans `logs/rotation.log`

---

## 🔍 Troubleshooting

### Permissions refusées sur macOS

Si vous avez des erreurs "Operation not permitted":

1. **Ouvrir:** Préférences Système → Sécurité et confidentialité
2. **Aller à:** Confidentialité → Accès complet au disque
3. **Ajouter:** Terminal.app (ou Cursor.app si vous utilisez Cursor)
4. **Redémarrer** l'application

### Le cron ne s'exécute pas

```bash
# Vérifier que cron est actif
ps aux | grep cron

# Sur macOS, vérifier les logs système
log show --predicate 'process == "cron"' --last 1d

# Tester le script manuellement
/Users/stephanecourant/Documents/DAZ/MCP/MCP/scripts/rotate_logs_daily.sh
```

### LaunchAgent ne démarre pas

```bash
# Vérifier les erreurs
launchctl error com.mcp.logrotate

# Voir les logs système
log show --predicate 'subsystem == "com.apple.launchd"' --last 1h | grep mcp
```

---

## 📝 Recommandation finale

**Pour macOS:** Utiliser **Méthode 2 (LaunchAgent)** - c'est le système natif et le plus fiable.

**Pour Linux/Production:** Utiliser **logrotate** (déjà configuré dans `/tmp/mcp-logrotate.conf`)

---

## 📚 Documentation

- Script principal: [scripts/rotate_logs_daily.sh](scripts/rotate_logs_daily.sh)
- Configuration: [scripts/setup_log_rotation.sh](scripts/setup_log_rotation.sh)
- Rapport nettoyage: [NETTOYAGE_LOGS_21OCT2025.md](NETTOYAGE_LOGS_21OCT2025.md)

---

**Prochaine action:** Choisir et activer **Méthode 1** ou **Méthode 2** ci-dessus. ✨

