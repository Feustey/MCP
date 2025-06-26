#!/bin/bash

# Script principal de déploiement pour api.dazno.de
# Ce script orchestre le déploiement complet de l'API avec SSL

set -e

# Variables
DOMAIN="api.dazno.de"
APP_DIR="/var/www/mcp"
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Fonction pour afficher la progression
show_step() {
    echo -e "\n🚀 Étape $1/$2: $3"
}

# Fonction pour vérifier les prérequis
check_prerequisites() {
    echo "🔍 Vérification des prérequis..."
    
    # Vérification de l'utilisateur root
    if [ "$EUID" -ne 0 ]; then
        echo "❌ Ce script doit être exécuté en tant que root"
        exit 1
    fi

    # Vérification de Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker n'est pas installé"
        exit 1
    fi

    # Vérification de Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose n'est pas installé"
        exit 1
    fi

    # Vérification de Nginx
    if ! command -v nginx &> /dev/null; then
        echo "❌ Nginx n'est pas installé"
        exit 1
    fi

    echo "✅ Tous les prérequis sont satisfaits"
}

# Fonction pour préparer l'environnement
prepare_environment() {
    echo "🔧 Préparation de l'environnement..."
    
    # Création des répertoires nécessaires
    mkdir -p "$APP_DIR"
    
    # Vérification des scripts nécessaires
    for script in clean_nginx_config.sh deploy_ssl_complete.sh verify_ssl.sh; do
        if [ ! -f "$SCRIPTS_DIR/$script" ]; then
            echo "❌ Script manquant : $script"
            exit 1
        fi
        chmod +x "$SCRIPTS_DIR/$script"
    done
}

# Fonction pour le déploiement
deploy() {
    local total_steps=4
    
    # Étape 1: Nettoyage de la configuration Nginx
    show_step 1 $total_steps "Nettoyage de la configuration Nginx"
    bash "$SCRIPTS_DIR/clean_nginx_config.sh"
    
    # Étape 2: Déploiement SSL
    show_step 2 $total_steps "Déploiement SSL"
    bash "$SCRIPTS_DIR/deploy_ssl_complete.sh"
    
    # Étape 3: Vérification du déploiement
    show_step 3 $total_steps "Vérification du déploiement"
    bash "$SCRIPTS_DIR/verify_ssl.sh"
    
    # Étape 4: Tests finaux
    show_step 4 $total_steps "Tests finaux"
    echo "🌐 Test de l'API..."
    if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/health"; then
        echo "✅ L'API répond correctement"
    else
        echo "❌ L'API ne répond pas correctement"
        echo "📋 Logs des conteneurs :"
        cd "$APP_DIR" && docker-compose logs --tail=50
        exit 1
    fi
}

# Fonction principale
main() {
    echo "🚀 Début du déploiement pour $DOMAIN"
    
    # Vérification des prérequis
    check_prerequisites
    
    # Préparation de l'environnement
    prepare_environment
    
    # Déploiement
    deploy
    
    echo -e "\n✨ Déploiement terminé avec succès !"
    echo "📋 Vérifiez https://$DOMAIN dans votre navigateur"
}

# Exécution du script
main 