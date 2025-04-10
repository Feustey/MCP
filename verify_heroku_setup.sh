#!/bin/bash

echo "🔍 Vérification de la configuration Heroku"

# Vérification des fichiers de configuration
echo "📄 Vérification des fichiers requis"
MISSING_FILES=0

check_file() {
  if [ -f "$1" ]; then
    echo "  ✅ $1 existe"
  else
    echo "  ❌ $1 manquant"
    MISSING_FILES=$((MISSING_FILES+1))
  fi
}

check_file "Procfile"
check_file "runtime.txt"
check_file "requirements.txt"
check_file "nltk.txt"
check_file "app.json"

if [ $MISSING_FILES -gt 0 ]; then
  echo "⚠️ Fichiers manquants: $MISSING_FILES. Exécutez setup_heroku.sh pour les créer."
else
  echo "✅ Tous les fichiers requis sont présents"
fi

# Vérification du Procfile
if [ -f "Procfile" ]; then
  PROCFILE_CONTENT=$(cat Procfile)
  if [[ $PROCFILE_CONTENT == *"gunicorn"* && $PROCFILE_CONTENT == *"app"* && $PROCFILE_CONTENT == *"PORT"* ]]; then
    echo "✅ Procfile correctement configuré"
  else
    echo "⚠️ Procfile peut ne pas être correctement configuré"
    echo "   Contenu actuel: $PROCFILE_CONTENT"
    echo "   Format attendu: web: gunicorn api:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:\$PORT"
  fi
fi

# Vérification de l'installation Heroku CLI
if command -v heroku >/dev/null 2>&1; then
  echo "✅ Heroku CLI est installé"
  
  # Vérifier si l'utilisateur est connecté
  HEROKU_AUTH=$(heroku auth:whoami 2>&1)
  if [[ $HEROKU_AUTH == *"Error"* ]]; then
    echo "⚠️ Vous n'êtes pas connecté à Heroku. Exécutez 'heroku login' pour vous connecter."
  else
    echo "✅ Connecté à Heroku en tant que: $HEROKU_AUTH"
    
    # Vérifier les addons MongoDB et Redis
    HEROKU_ADDONS=$(heroku addons 2>&1)
    if [[ $HEROKU_ADDONS == *"mongolab"* ]]; then
      echo "✅ MongoDB addon est installé"
    else
      echo "⚠️ MongoDB addon n'est pas installé. Exécutez setup_mongodb_heroku.sh"
    fi
    
    if [[ $HEROKU_ADDONS == *"heroku-redis"* ]]; then
      echo "✅ Redis addon est installé"
    else
      echo "⚠️ Redis addon n'est pas installé. Vous pourriez en avoir besoin."
    fi
  fi
else
  echo "❌ Heroku CLI n'est pas installé. Installez-le via https://devcenter.heroku.com/articles/heroku-cli"
fi

# Vérification de git
if command -v git >/dev/null 2>&1; then
  echo "✅ Git est installé"
  
  # Vérifier si le dépôt est initialisé
  if [ -d ".git" ]; then
    echo "✅ Dépôt Git initialisé"
    
    # Vérifier si Heroku est configuré comme remote
    GIT_REMOTES=$(git remote -v)
    if [[ $GIT_REMOTES == *"heroku"* ]]; then
      echo "✅ Remote Heroku configuré"
    else
      echo "⚠️ Remote Heroku non configuré. Exécutez 'heroku git:remote -a [NOM_APP]'"
    fi
  else
    echo "⚠️ Dépôt Git non initialisé. Exécutez 'git init'"
  fi
else
  echo "❌ Git n'est pas installé. Vous en aurez besoin pour déployer sur Heroku."
fi

echo "🎉 Vérification terminée!" 