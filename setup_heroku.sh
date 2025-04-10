#!/bin/bash

echo "🚀 Configuration de l'application pour Heroku"

# Vérification que le Procfile existe et est correct
if [ ! -f "Procfile" ]; then
  echo "web: gunicorn api:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:\$PORT" > Procfile
  echo "✅ Procfile créé"
else
  echo "✅ Procfile existant"
fi

# Vérification que runtime.txt existe et est correct
if [ ! -f "runtime.txt" ]; then
  echo "python-3.11.8" > runtime.txt
  echo "✅ runtime.txt créé"
else
  echo "✅ runtime.txt existant"
fi

# Vérification et mise à jour de nltk.txt
if [ ! -f "nltk.txt" ]; then
  cat > nltk.txt << EOF
punkt
averaged_perceptron_tagger
wordnet
stopwords
omw-1.4
EOF
  echo "✅ nltk.txt créé"
else
  echo "✅ nltk.txt existant"
fi

# Vérification et création du fichier app.json si nécessaire
if [ ! -f "app.json" ]; then
  cat > app.json << EOF
{
  "name": "mcp",
  "description": "Application MCP",
  "region": "eu",
  "env": {
    "HEROKU_REGION": {
      "required": true,
      "value": "eu"
    }
  }
}
EOF
  echo "✅ app.json créé"
else
  echo "✅ app.json existant"
fi

# Définition des buildpacks
echo "🔧 Configuration des buildpacks Heroku"
heroku buildpacks:clear || true
heroku buildpacks:add heroku/python
echo "✅ Buildpack Python ajouté"

# Ajout de Redis si nécessaire
if grep -q "REDIS_URL" .env || grep -q "REDIS_URL" .env.example; then
  heroku addons:create heroku-redis:mini --region eu || true
  echo "✅ Redis addon ajouté"
fi

# Mise à jour des variables d'environnement
echo "🔧 Configuration des variables d'environnement"
if [ -f ".env" ]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Ignorer les lignes vides ou commentées
    if [[ -n "$line" && "$line" != \#* ]]; then
      heroku config:set "$line" || true
    fi
  done < .env
  echo "✅ Variables d'environnement configurées"
else
  echo "⚠️ Fichier .env non trouvé, variables d'environnement non configurées"
fi

echo "🎉 Configuration terminée ! Vous pouvez maintenant déployer avec 'git push heroku main'" 