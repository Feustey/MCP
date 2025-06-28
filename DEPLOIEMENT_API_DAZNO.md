# 🚀 Guide de déploiement pour api.dazno.de

**Dernière mise à jour:** 9 mai 2025

## 📋 Résumé du problème

L'API sur `api.dazno.de` retourne actuellement une **erreur 502 (Bad Gateway)** car :
- ✅ Le serveur web Caddy fonctionne (port 443 accessible)
- ✅ Le certificat SSL Let's Encrypt est valide
- ❌ L'application FastAPI n'est pas démarrée (aucun port backend accessible)

## 🔧 Solutions disponibles

### 1. **Script de déploiement automatique** (recommandé)
```bash
# Si vous avez accès SSH avec clés configurées
./scripts/deploy_api_dazno.sh
```

### 2. **Déploiement manuel** (si pas d'accès SSH)
```bash
# Afficher les instructions
./scripts/deploy_complete.sh
```

### 3. **Diagnostic rapide**
```bash
# Test de connectivité
./scripts/test_api_dazno.sh

# Diagnostic de l'erreur 502
./scripts/fix_502_api.sh

# Test des ports backend
./scripts/test_backend_ports.sh
```

## 📦 Fichiers de configuration prêts

### Configuration Caddy
**Fichier:** `config/caddy/Caddyfile.api.dazno.de`
```caddy
api.dazno.de {
    reverse_proxy localhost:8000 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
        header_up Host {host}
    }
    
    log {
        output file /var/log/caddy/api.dazno.de.log
        format json
    }
    
    handle_errors {
        respond "{err.status_code} {err.status_text}" {err.status_code}
    }
    
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        X-XSS-Protection "1; mode=block"
        Referrer-Policy strict-origin-when-cross-origin
        Access-Control-Allow-Origin *
        Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
        Access-Control-Allow-Headers "Content-Type, Authorization"
        Cache-Control "public, max-age=3600" /static/*
        Cache-Control "no-cache" /api/*
    }
    
    encode gzip
}
```

### Service systemd
**Fichier:** `config/systemd/mcp-api.service`
```ini
[Unit]
Description=MCP API Service
Documentation=https://github.com/Feustey/MCP
After=network.target
Wants=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/mcp
Environment=PATH=/var/www/mcp/venv/bin
Environment=PYTHONPATH=/var/www/mcp
Environment=PYTHONUNBUFFERED=1

ExecStart=/var/www/mcp/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

Restart=always
RestartSec=10

LimitNOFILE=65536
LimitNPROC=4096

StandardOutput=journal
StandardError=journal
SyslogIdentifier=mcp-api

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/www/mcp /var/log

TimeoutStartSec=30
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

## 🚀 Instructions de déploiement manuel

### Étape 1: Accès au serveur
- Connectez-vous à votre panneau de contrôle Hostinger
- Ou utilisez le terminal SSH de Hostinger

### Étape 2: Préparation
```bash
mkdir -p /var/www/mcp
cd /var/www/mcp
```

### Étape 3: Téléchargement du code
```bash
git clone https://github.com/Feustey/MCP.git .
```

### Étape 4: Configuration Python
```bash
apt update && apt install -y python3 python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-hostinger.txt
```

### Étape 5: Configuration du service
```bash
# Copier le fichier de service
cp config/systemd/mcp-api.service /etc/systemd/system/
```

### Étape 6: Configuration Caddy
```bash
# Copier le fichier de configuration
cp config/caddy/Caddyfile.api.dazno.de /etc/caddy/Caddyfile
```

### Étape 7: Démarrage des services
```bash
systemctl daemon-reload
systemctl enable mcp-api
systemctl start mcp-api
systemctl restart caddy
```

### Étape 8: Vérification
```bash
# Vérifier le statut
systemctl status mcp-api
systemctl status caddy

# Vérifier les logs
journalctl -u mcp-api -f
tail -f /var/log/caddy/api.dazno.de.log

# Test local
curl http://localhost:8000/health
```

## 🔍 Diagnostic et dépannage

### Commandes de diagnostic
```bash
# Vérifier les services
systemctl list-units --type=service --state=active | grep -E '(caddy|mcp|fastapi)'

# Vérifier les ports
netstat -tlnp | grep -E ':(80|443|8000)'

# Vérifier les processus
ps aux | grep -E '(python|uvicorn|fastapi)'

# Logs Caddy
tail -f /var/log/caddy/api.dazno.de.log
```

### Problèmes courants

1. **Erreur 502 persistante**
   - Vérifiez que l'API est démarrée: `systemctl status mcp-api`
   - Vérifiez les logs: `journalctl -u mcp-api -f`
   - Testez localement: `curl http://localhost:8000/health`

2. **Service ne démarre pas**
   - Vérifiez les permissions: `chown -R www-data:www-data /var/www/mcp`
   - Vérifiez les dépendances: `pip list`
   - Vérifiez la configuration: `cat /etc/systemd/system/mcp-api.service`

3. **Caddy ne fonctionne pas**
   - Vérifiez la configuration: `cat /etc/caddy/Caddyfile`
   - Vérifiez les logs: `tail -f /var/log/caddy/api.dazno.de.log`
   - Redémarrez: `systemctl restart caddy`

## 📞 Support

Si vous rencontrez des problèmes :

1. **Vérifiez les logs:**
   ```bash
   journalctl -u mcp-api -f
   tail -f /var/log/caddy/api.dazno.de.log
   ```

2. **Testez localement:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Vérifiez la configuration:**
   ```bash
   cat /etc/caddy/Caddyfile
   cat /etc/systemd/system/mcp-api.service
   ```

4. **Redémarrez les services:**
   ```bash
   systemctl restart mcp-api caddy
   ```

## ✅ Vérification finale

Après le déploiement, testez :

```bash
# Test HTTPS
curl -s -o /dev/null -w "HTTPS - Code: %{http_code}\n" https://api.dazno.de/health

# Test HTTP (redirection)
curl -s -o /dev/null -w "HTTP - Code: %{http_code}\n" http://api.dazno.de/health

# Test documentation
curl -s -o /dev/null -w "Docs - Code: %{http_code}\n" https://api.dazno.de/docs
```

**Résultat attendu :** Code 200 pour tous les tests. 