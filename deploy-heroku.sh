#!/bin/bash

# Script de déploiement automatique pour Heroku
# Utilisation : chmod +x deploy-heroku.sh && ./deploy-heroku.sh

# Vérification des dépendances
check_dependencies() {
  command -v git >/dev/null 2>&1 || { echo >&2 "Erreur: Git doit être installé"; exit 1; }
  command -v heroku >/dev/null 2>&1 || { echo >&2 "Erreur: Heroku CLI doit être installé"; exit 1; }
}

# Configuration initiale
setup_heroku() {
  # Login Heroku
  heroku login -i

  # Création de l'application
  APP_NAME="mcp-${RANDOM}"
  heroku create $APP_NAME

  # Configuration des buildpacks
  heroku buildpacks:add heroku/python -a $APP_NAME
  heroku buildpacks:add heroku/redis -a $APP_NAME

  # Addon Redis
  heroku addons:create heroku-redis:mini -a $APP_NAME
}

# Déploiement du code
deploy_app() {
  # Création du Procfile si inexistant
  if [ ! -f Procfile ]; then
    echo "web: gunicorn app:app" > Procfile
  fi

  # Fichier requirements.txt
  pip freeze > requirements.txt

  # Déploiement Git
  git init
  git add .
  git commit -m "Deploiement Heroku automatique"
  git push heroku main

  # Configuration des variables d'environnement
  if [ -f .env ]; then
    while read line; do
      if [ ! -z "$line" ] && [[ $line != \#* ]]; then
        heroku config:set $line -a $APP_NAME
      fi
    done < .env
  fi
}

# Vérification finale
verify_deployment() {
  heroku open -a $APP_NAME
  heroku logs --tail -a $APP_NAME
}

# Exécution principale
main() {
  echo "=== Vérification des dépendances ==="
  check_dependencies

  echo "=== Configuration Heroku ==="
  setup_heroku

  echo "=== Déploiement de l'application ==="
  deploy_app

  echo "=== Vérification du déploiement ==="
  verify_deployment
}

# Lancement du script
main