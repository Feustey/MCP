# Optimisation du déploiement Heroku

Ce document décrit les optimisations réalisées pour réduire la taille du slug lors du déploiement sur Heroku.

## Problématique

Heroku impose une limite de 500 Mo pour la taille du slug. Les fichiers JSON volumineux dans le dossier `collected_data/` alourdissent le slug et peuvent causer des problèmes lors du déploiement.

## Solution

Nous avons mis en place une solution de migration des données JSON vers MongoDB :

1. **Modification de `mongo_operations.py`**
   - Ajout de méthodes pour stocker et récupérer les données de centralités et de résumés réseau
   - Méthodes pour sauvegarder directement dans MongoDB et récupérer depuis MongoDB

2. **Modification de `data_aggregator.py`**
   - Utilisation de MongoDB au lieu des fichiers JSON
   - Conservation de la compatibilité avec les fichiers JSON pour les systèmes existants
   - Récupération de données depuis MongoDB en priorité

3. **Scripts de migration**
   - `migrate_json_to_mongo.py` : Script complexe avec dépendances avancées
   - `simple_migration.py` : Script simplifié pour migrer facilement les données
   - `test_mongo_migration.py` : Script de test pour vérifier la migration

4. **Mise à jour du `.slugignore`**
   - Exclusion du dossier `collected_data/` pour réduire la taille du slug

## Avantages

Cette approche présente plusieurs avantages :

- **Réduction de la taille du slug** : Les fichiers JSON volumineux ne sont plus inclus dans le déploiement
- **Meilleure performance** : Accès aux données plus rapide via MongoDB
- **Scalabilité** : MongoDB permet une meilleure gestion des données volumineuses
- **Compatibilité** : Le code maintient la compatibilité avec les fichiers JSON pour une transition en douceur

## Utilisation

### Migration des données

Pour migrer les données JSON vers MongoDB :

```bash
python simple_migration.py
```

Le script vous guidera à travers les étapes suivantes :
1. Sauvegarde des fichiers JSON dans un dossier de backup
2. Migration des données vers MongoDB
3. Mise à jour de `.slugignore`
4. Option de suppression des fichiers JSON originaux

### Récupération des données

En cas de besoin, vous pouvez restaurer les fichiers JSON depuis :
- Le répertoire `json_backup/`
- Les fichiers `.bak` dans `collected_data/`

## Tests

Pour tester la migration sans effectuer de modifications :

```bash
python test_mongo_migration.py
```

Ce script vérifie la connexion à MongoDB et teste la migration des fichiers JSON clés.

## Déploiement sur Heroku

Après la migration, le déploiement sur Heroku devrait être plus léger et plus rapide. La taille du slug devrait être considérablement réduite, bien en dessous de la limite de 500 Mo.

Pour vérifier la taille du slug après déploiement :

```bash
heroku slug:size
```

## Configuration requise

- MongoDB (Atlas ou autre instance)
- Variables d'environnement MongoDB configurées (`DATABASE_URL`)
- Python 3.6+ avec les packages `pymongo` et `motor`

## Référence

- [Documentation Heroku sur la taille des slugs](https://devcenter.heroku.com/articles/slug-compiler#slug-size)
- [Documentation MongoDB](https://docs.mongodb.com/) 