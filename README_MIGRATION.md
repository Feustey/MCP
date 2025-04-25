# Migration des données JSON vers MongoDB

Ce document explique comment utiliser les scripts fournis pour migrer les données JSON volumineuses vers MongoDB.

## Contexte

Les fichiers JSON volumineux dans le dossier `collected_data/` peuvent poser problème lors du déploiement sur Heroku en raison de la limite de 500 Mo pour la taille du slug. La migration de ces données vers MongoDB permet de réduire considérablement la taille du slug tout en améliorant les performances d'accès aux données.

## Vérification de la taille du slug

Avant de procéder à la migration, vous pouvez vérifier la taille actuelle du slug avec le script `check_heroku_slug_size.py` :

```bash
python check_heroku_slug_size.py
```

Ce script :
- Détecte l'application Heroku associée
- Liste les fichiers et répertoires exclus dans `.slugignore`
- Calcule la taille estimée du slug
- Identifie les éléments les plus volumineux
- Fournit des recommandations si la taille approche la limite

## Migration vers MongoDB

### Option 1 : Migration simplifiée

Le script `simple_migration.py` est la solution la plus simple pour migrer les données. Il ne nécessite que `pymongo` et les bibliothèques standard de Python.

```bash
python simple_migration.py
```

Le script vous guidera à travers ces étapes :
1. Sauvegarde des fichiers JSON dans un dossier `json_backup/`
2. Migration des données vers MongoDB
3. Mise à jour de `.slugignore` pour exclure le dossier `collected_data/`
4. Option de suppression des fichiers JSON originaux (avec sauvegarde `.bak`)

### Option 2 : Migration avancée

Pour une migration plus avancée avec des tests et une meilleure gestion des erreurs, vous pouvez utiliser la combinaison de scripts suivante :

1. Test de la migration :
   ```bash
   python test_mongo_migration.py
   ```

2. Exécution de la migration complète :
   ```bash
   python run_migration.py
   ```

## Fonctionnement avec les applications existantes

La migration est conçue pour fonctionner en douceur avec le code existant :

1. `data_aggregator.py` a été modifié pour :
   - Chercher d'abord les données dans MongoDB
   - Utiliser les API sources si les données ne sont pas en cache
   - Sauvegarder les nouvelles données dans MongoDB
   - Conserver la compatibilité avec le code existant

2. `mongo_operations.py` a été étendu avec de nouvelles méthodes pour :
   - Sauvegarder les données de centralités et résumés réseau
   - Récupérer les dernières données disponibles
   - Migrer des fichiers JSON vers MongoDB

## Restauration des données

Si vous avez besoin de revenir à l'approche basée sur fichiers JSON, vous pouvez :

1. Restaurer les fichiers depuis le répertoire `json_backup/`
2. Ou récupérer les fichiers `.bak` dans `collected_data/`
3. Modifier `.slugignore` pour ne pas exclure `collected_data/`

## Configuration requise

- MongoDB (Atlas ou autre instance)
- Variable d'environnement `DATABASE_URL` configurée
- Packages Python : `pymongo` et `motor`

## Vérification après migration

Pour vérifier que la migration a fonctionné et que l'application utilise bien MongoDB :

1. Exécutez à nouveau `check_heroku_slug_size.py` pour confirmer la réduction de taille
2. Testez l'application avec `pytest` pour vérifier que tout fonctionne correctement
3. Déployez sur Heroku et confirmez que le déploiement réussit

## Documentation détaillée

Pour plus d'informations sur l'optimisation pour Heroku, consultez :
- `HEROKU_OPTIMISATION.md` pour une description détaillée des optimisations
- La [documentation Heroku sur la taille des slugs](https://devcenter.heroku.com/articles/slug-compiler#slug-size) 