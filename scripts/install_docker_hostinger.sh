#!/bin/bash
set -e

# Configuration
REMOTE_USER="root"
REMOTE_HOST="147.79.101.32"
REMOTE_PORT="22"

echo "🔧 Installation de Docker sur Hostinger..."

ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
    # Mise à jour du système
    apt-get update
    apt-get install -y apt-transport-https ca-certificates curl software-properties-common

    # Installation des dépôts Docker
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    # Ajout du repository Docker
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Installation de Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Configuration du démon Docker
    cat > /etc/docker/daemon.json << 'INNEREOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-address-pools": [
    {
      "base": "172.17.0.0/16",
      "size": 24
    }
  ]
}
INNEREOF

    # Redémarrage de Docker
    systemctl restart docker
    
    # Test de l'installation
    docker run --rm hello-world
EOF

echo "✅ Installation de Docker terminée" 