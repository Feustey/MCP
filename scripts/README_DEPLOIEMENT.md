# Guide de déploiement MCP

Dernière mise à jour: 9 mai 2025

## Problème résolu

L'application MCP rencontrait des erreurs de validation Pydantic car certaines variables d'environnement étaient marquées comme requises (`Field(..., ...)`) mais n'étaient pas fournies.

## Solutions disponibles

### 1. Script minimal (Recommandé pour test rapide)
```bash
sh scripts/start_minimal.sh
```
- Variables minimales avec valeurs par défaut
- Évite les erreurs de validation
- Idéal pour tester rapidement

### 2. Script avec configuration de développement
```bash
sh scripts/start_with_dev_config.sh
```
- Remplace temporairement `config.py` par `config_dev.py`
- Toutes les variables ont des valeurs par défaut
- Restaure automatiquement la config originale à l'arrêt
- Mode développement avec reload automatique

### 3. Script complet avec toutes les variables
```bash
sh scripts/start_direct.sh
```
- Toutes les variables d'environnement définies
- Configuration complète pour production
- Nécessite de modifier les clés API

### 4. Script simple avec vérifications
```bash
sh scripts/start_simple.sh
```
- Vérifie les dépendances
- Test de configuration
- Variables complètes

## Variables d'environnement requises

### Variables principales (Hostinger)
```bash
export MONGO_URL="mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true"
export REDIS_HOST="d4s8888skckos8c80w4swgcw"
export REDIS_PORT="6379"
export REDIS_USERNAME="default"
export REDIS_PASSWORD="YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1"
export ENVIRONMENT="production"
```

### Variables requises par Pydantic
```bash
export AI_OPENAI_API_KEY="your_openai_api_key_here"
export SECURITY_SECRET_KEY="your_secret_key_here"
```

## Scripts utilitaires

### Test de configuration
```bash
python3 scripts/test_config.py
```

### Test de configuration développement
```bash
python3 scripts/test_config_dev.py
```

### Restauration de configuration
```bash
sh scripts/restore_config.sh
```

## Démarrage recommandé

1. **Pour tester rapidement** :
   ```bash
   sh scripts/start_minimal.sh
   ```

2. **Pour développement** :
   ```bash
   sh scripts/start_with_dev_config.sh
   ```

3. **Pour production** :
   - Modifier les clés API dans `scripts/start_direct.sh`
   - Exécuter : `sh scripts/start_direct.sh`

## Résolution des erreurs

### Erreur "Field required"
- Utiliser `start_minimal.sh` ou `start_with_dev_config.sh`
- Ou définir toutes les variables requises

### Erreur "No module named 'config'"
- Vérifier que le fichier `config.py` existe
- Utiliser `start_with_dev_config.sh` qui gère automatiquement

### Erreur de dépendances
- Exécuter : `pip install -r requirements-hostinger.txt`

## Notes importantes

- Les scripts utilisent `sh` au lieu de `bash` pour compatibilité
- La configuration de développement a des valeurs par défaut pour éviter les erreurs
- En production, remplacer les clés API par de vraies valeurs
- Le script `start_with_dev_config.sh` restaure automatiquement la configuration originale 