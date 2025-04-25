# Guide des Tests MCP

Ce guide explique comment écrire et exécuter des tests pour le projet MCP.

## Architecture des Tests

- `tests/` : Répertoire principal des tests
  - `conftest.py` : Configuration globale pour pytest
  - `test_*.py` : Fichiers de tests individuels
  - `mocks/` : Mocks et données de test
  - `load_tests/` : Tests de performance

## Bonnes Pratiques

### Tests Asynchrones

Pour les tests asynchrones, utilisez l'approche directe avec des mocks plutôt que des fixtures asyncio:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_async_function():
    # Créer un mock directement dans le test
    mock_obj = MagicMock()
    mock_obj.async_method = AsyncMock(return_value={"data": "test"})
    
    # Appeler la méthode async
    result = await mock_obj.async_method()
    
    # Assertions
    assert result == {"data": "test"}
```

### Utilisation des Mocks Standardisés

Utilisez la fixture `standard_mocks` pour accéder à des mocks préconfigurés:

```python
@pytest.mark.asyncio
async def test_with_standard_mocks(standard_mocks):
    # Utilisation du mock OpenAI standardisé
    with patch("openai.AsyncClient", return_value=standard_mocks["openai"]):
        # Test avec le mock standardisé
        result = await my_function_using_openai()
        assert result is not None
    
    # Utilisation du mock Redis standardisé
    with patch("redis.asyncio.Redis.from_url", return_value=standard_mocks["redis"]):
        # Test avec le mock standardisé
        result = await my_function_using_redis()
        assert result is not None
```

### Migration vers Pydantic V2

- Utilisez `pydantic-settings` au lieu de `BaseSettings` de pydantic
- Utilisez `field_validator` au lieu de `validator`
- Utilisez `model_config` au lieu de `Config`
- Utilisez `json_schema_extra` au lieu de `schema_extra`

Exemple :

```python
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings

class MySettings(BaseSettings):
    # Champs
    
    model_config = {
        "env_file": ".env"
    }

class MyModel(BaseModel):
    # Champs
    
    @field_validator('field_name')
    @classmethod
    def validate_field(cls, v, info):
        # Validation
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": { ... }
        }
    }
```

### Tests avec Mock

Pour mocker des classes, utilisez `MagicMock` avec une spécification claire :

```python
from unittest.mock import MagicMock, AsyncMock

# Pour une classe normale
mock_obj = MagicMock(spec=MyClass)

# Pour les méthodes asynchrones
mock_obj.async_method = AsyncMock(return_value=expected_result)

# Pour simuler différents retours
mock_obj.method.side_effect = [result1, result2, exception]
```

## Exécution des Tests

### Lancer tous les tests

```bash
python -m pytest
```

### Lancer des tests spécifiques

```bash
python -m pytest tests/test_specific.py
```

### Mode verbeux

```bash
python -m pytest -v
```

### Lancer les tests asynchrones

```bash
python -m pytest --asyncio-mode=strict
```

### Lancer les tests avec couverture

```bash
# Rapport de couverture basique
python -m pytest --cov=src

# Rapport détaillé avec HTML
python -m pytest --cov=src --cov-report=term --cov-report=html

# Rapport avec lignes manquantes
python -m pytest --cov=src --cov-report=term-missing
```

### Lancer les tests de performance

```bash
python -m pytest tests/load_tests/test_rag_performance.py -v
```

## Couverture de Code

### Objectifs de Couverture

- **Cible minimale** : 80% de couverture globale
- **Cible pour le code critique** : 90% ou plus

### Visualisation du Rapport

Après avoir généré le rapport HTML, vous pouvez l'ouvrir avec:

```bash
open htmlcov/index.html
```

### Exclusions de Couverture

Certaines parties du code sont exclues de l'analyse de couverture:
- Code de migration
- Code d'initialisation
- Code généré automatiquement

Pour marquer du code à exclure de la couverture:

```python
def function_not_to_be_covered():  # pragma: no cover
    # Ce code sera exclu de l'analyse de couverture
    pass
```

## Résolution des Problèmes

### Erreur : 'async_generator' object has no attribute

Si vous rencontrez cette erreur avec des fixtures asyncio, évitez d'utiliser des fixtures asynchrones et préférez l'approche directe avec des mocks comme montré dans les exemples.

### Avertissements Pydantic

Si vous voyez des avertissements concernant des fonctionnalités dépréciées de Pydantic, assurez-vous de migrer le code vers Pydantic V2 en utilisant les directives ci-dessus. 