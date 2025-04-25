#!/bin/bash

# Configuration Heroku
heroku config:set PORT=8000
heroku config:set ENVIRONMENT=production
heroku config:set MONGODB_URI="mongodb+srv://feustey:VwSrcnNI8i5m2sim@dazlng.ug0aiaw.mongodb.net/?retryWrites=true&w=majority&appName=DazTest"
heroku config:set OPENAI_API_KEY="votre_clé_openai"
heroku config:set SPARKSEER_API_KEY="votre_clé_sparkseer"
heroku config:set AMBOSS_API_KEY="votre_clé_amboss"
heroku config:set LNBITS_API_KEY="votre_clé_lnbits"

# Vérification
echo "Vérification des variables d'environnement :"
heroku config
