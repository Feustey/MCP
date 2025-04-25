# Guide de Maintenance et d'Extension des Tests

Ce document fournit des directives pour maintenir et étendre efficacement la suite de tests du projet MCP.

## Maintenance des Tests Existants

### Révision Périodique des Tests

Pour maintenir la qualité des tests, effectuez régulièrement les actions suivantes :

- **Audit trimestriel** : Revue complète des tests pour identifier les obsolètes ou redondants
- **Mise à jour des fixtures** : Vérifier que les fixtures reflètent l'état actuel du système
- **Nettoyage des mocks** : S'assurer que les mocks correspondent aux interfaces actuelles

### Refactorisation des Tests

Lors de la refactorisation du code de production, mettez à jour les tests en suivant ces principes :

```python
# ❌ Ancien test fragile
def test_old_api():
    result = old_api_function("input")
    assert result == "expected output"

# ✅ Test refactorisé robuste
def test_new_api():
    # Commentaire expliquant la transition
    result = new_api_function("input")
    assert result.data == "expected output"
    assert result.status == "success"
```

### Dépannage des Tests Défaillants

Lorsqu'un test échoue, suivez cette procédure de diagnostic :

1. **Isoler** : Exécuter le test séparément pour confirmer l'échec
2. **Examiner** : Analyser les logs et la sortie d'erreur
3. **Reproduire** : Identifier les conditions exactes de l'échec
4. **Corriger** : Résoudre le problème dans le code ou adapter le test

## Extension de la Suite de Tests

### Ajout de Nouveaux Tests

Pour ajouter de nouveaux tests, suivez ces étapes :

1. **Identifier les besoins** : Déterminer quelles fonctionnalités manquent de couverture
2. **Choisir le type de test** : Unitaire, intégration, ou performance
3. **Créer le fichier** : Respecter les conventions de nommage (`test_*.py`)
4. **Implémenter les tests** : Suivre le pattern AAA (Arrange-Act-Assert)
5. **Documenter** : Ajouter des docstrings et commentaires explicatifs

```python
"""
Ce module teste la fonctionnalité X qui est critique pour Y.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_new_feature():
    """
    Vérifie que la nouvelle fonctionnalité gère correctement les entrées valides.
    """
    # Arrange
    test_input = "valid_input"
    expected_output = "expected_result"
    mock_dependency = AsyncMock(return_value="mocked_data")
    
    # Act
    result = await new_feature(test_input, dependency=mock_dependency)
    
    # Assert
    assert result == expected_output
    mock_dependency.assert_called_once_with(test_input)
```

### Création de Fixtures Réutilisables

Les fixtures permettent le partage de logique de test :

```python
@pytest.fixture
async def mock_database():
    """Fixture fournissant une base de données mockée pour les tests."""
    db = AsyncMock()
    db.find_one.return_value = {"test": "data"}
    db.insert_one.return_value = MagicMock(inserted_id="test_id")
    yield db
    # Nettoyage optionnel
```

### Extension des Tests de Performance

Pour étendre les tests de performance :

1. **Définir les métriques** : Identifier les métriques clés à mesurer
2. **Créer des scénarios** : Élaborer des scénarios de test réalistes
3. **Établir des seuils** : Définir des limites acceptables pour chaque métrique
4. **Implémenter le test** : Utiliser le framework de tests de charge existant

```python
@pytest.mark.performance
async def test_rag_query_performance():
    """
    Teste la performance des requêtes RAG sous charge.
    Seuil d'acceptation : p95 < 800ms pour 50 requêtes simultanées.
    """
    # Configuration du test
    concurrent_users = 50
    queries_per_user = 5
    
    # Exécution du test
    results = await run_performance_test(
        concurrent_users=concurrent_users,
        queries_per_user=queries_per_user,
        test_duration_seconds=60
    )
    
    # Vérification des métriques
    assert results.p95_response_time < 0.8, "Le temps de réponse p95 dépasse 800ms"
    assert results.success_rate > 0.99, "Le taux de succès est inférieur à 99%"
```

## Éviter les Tests Fragiles

### Causes Courantes de Fragilité

- **Dépendances externes** : Reliance sur des services tiers non mockés
- **Données variables** : Utilisation de timestamps ou identifiants aléatoires non contrôlés
- **Ordre d'exécution** : Dépendance à l'ordre d'exécution des tests
- **État global** : Modification d'un état global sans nettoyage

### Bonnes Pratiques pour des Tests Robustes

```python
# ❌ Test fragile avec dépendance externe
def test_fragile():
    result = api_client.get_real_data()
    assert len(result) > 0

# ✅ Test robuste avec mock
def test_robust(mocker):
    mock_client = mocker.patch('module.api_client')
    mock_client.get_real_data.return_value = ["test_data"]
    
    result = api_client.get_real_data()
    assert len(result) == 1
```

## Tests Asynchrones

### Bonnes Pratiques pour les Tests Asynchrones

```python
@pytest.mark.asyncio
async def test_async_function():
    """
    Exemple de test asynchrone robuste.
    """
    # Préférer cette approche directe avec mocks
    mock_obj = MagicMock()
    mock_obj.async_method = AsyncMock(return_value={"data": "test"})
    
    # Appeler la méthode async
    result = await mock_obj.async_method()
    
    # Assertions
    assert result == {"data": "test"}
```

## Mesure et Amélioration de la Couverture

### Analyse de Couverture

```bash
# Exécuter les tests avec couverture
python -m pytest --cov=src --cov-report=term --cov-report=html

# Vérifier les zones à faible couverture
python -m pytest --cov=src --cov-report=term-missing
```

### Stratégies d'Amélioration de la Couverture

1. **Identifier les lacunes** : Utiliser les rapports de couverture pour trouver le code non testé
2. **Prioriser** : Se concentrer d'abord sur le code critique et complexe
3. **Ajouter des tests ciblés** : Écrire des tests spécifiques pour les branches manquantes
4. **Refactoriser le code difficile à tester** : Rendre le code plus testable

## Ressources Complémentaires

- [Stratégie de Test](./testing-strategy.md)
- [Tests par Composant](./component-testing.md)
- [Configuration de l'Environnement de Test](./test-environment.md) 