#!/bin/bash

echo "🔍 Démarrage des vérifications pré-déploiement..."

# 1. Vérification des fichiers
echo "📁 Vérification des fichiers critiques..."
files=("Procfile" "requirements.txt" "runtime.txt" "wsgi.py" ".slugignore" "nltk.txt")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file existe"
    else
        echo "❌ $file manquant"
        exit 1
    fi
done

# 2. Test de l'environnement virtuel
echo "🐍 Test de l'environnement virtuel..."
python -m venv test_venv
source test_venv/bin/activate
if pip install -r requirements.txt; then
    echo "✅ Installation des dépendances réussie"
else
    echo "❌ Erreur d'installation des dépendances"
    exit 1
fi

# 3. Tests
echo "🧪 Exécution des tests..."
if python -m pytest tests/; then
    echo "✅ Tests unitaires réussis"
else
    echo "❌ Échec des tests unitaires"
    exit 1
fi

# 4. Vérification des connexions
echo "🔌 Test des connexions externes..."
python test_mongo_connection.py
python test_openai_connection.py
python test_lnbits_connection.py

# 5. Nettoyage
echo "🧹 Nettoyage..."
./clean-build.sh

echo "✨ Vérifications terminées avec succès !"