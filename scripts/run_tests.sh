#!/bin/bash
# Script pour exécuter les tests localement

# Vérification de l'environnement virtuel
if [ -z "$VIRTUAL_ENV" ]; then
    echo "ATTENTION: Vous n'êtes pas dans un environnement virtuel. Activation de venv..."
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "Erreur: L'environnement virtuel venv n'existe pas. Exécutez 'python -m venv venv' pour le créer."
        exit 1
    fi
fi

# Création des répertoires pour les rapports
mkdir -p reports/coverage

# Installation des dépendances de test si nécessaires
if ! pip list | grep -q "pytest-cov"; then
    echo "Installation des dépendances de test..."
    pip install -e ".[test]"
    pip install pytest-cov
fi

# Définition des variables d'environnement pour le test
export ENVIRONMENT="test"
export MONGODB_URI="mongodb://localhost:27017/test"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET="test_jwt_secret"

# Vérification de MongoDB
echo "Vérification de MongoDB..."
nc -z localhost 27017 || { echo "Erreur: MongoDB n'est pas accessible. Démarrez MongoDB."; exit 1; }

# Vérification de Redis
echo "Vérification de Redis..."
nc -z localhost 6379 || { echo "Erreur: Redis n'est pas accessible. Démarrez Redis."; exit 1; }

# Exécution des tests unitaires uniquement
if [ "$1" == "unit" ]; then
    echo "Exécution des tests unitaires uniquement..."
    python -m pytest tests/unit -v --cov=src --cov=app --cov=mcp --cov=rag --cov-report=term-missing --cov-report=html:reports/coverage
    exit $?
fi

# Exécution des tests d'intégration uniquement
if [ "$1" == "integration" ]; then
    echo "Exécution des tests d'intégration uniquement..."
    python -m pytest tests/integration -v
    exit $?
fi

# Exécution du simulateur
if [ "$1" == "simulator" ]; then
    echo "Exécution des tests du simulateur..."
    python -m pytest tests/unit/test_stochastic_simulator.py -v
    exit $?
fi

# Exécution de tous les tests
echo "Exécution de tous les tests..."
python -m pytest --cov=src --cov=app --cov=mcp --cov=rag --cov-report=term-missing --cov-report=html:reports/coverage

# Affichage du résultat
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Tous les tests ont réussi"
    echo "Rapport de couverture généré dans: reports/coverage/index.html"
else
    echo "❌ Certains tests ont échoué"
fi

exit $EXIT_CODE 