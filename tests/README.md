# Guide des Tests MCP

Ce guide explique comment écrire et exécuter des tests pour le projet MCP.

## Architecture des Tests

- `tests/` : Répertoire principal des tests
  - `conftest.py` : Configuration globale pour pytest
  - `test_*.py` : Fichiers de tests individuels
  - `mocks/` : Mocks et données de test

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

## Résolution des Problèmes

### Erreur : 'async_generator' object has no attribute

Si vous rencontrez cette erreur avec des fixtures asyncio, évitez d'utiliser des fixtures asynchrones et préférez l'approche directe avec des mocks comme montré dans les exemples.

### Avertissements Pydantic

Si vous voyez des avertissements concernant des fonctionnalités dépréciées de Pydantic, assurez-vous de migrer le code vers Pydantic V2 en utilisant les directives ci-dessus. 