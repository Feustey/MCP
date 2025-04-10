# Guide de Déploiement sur Heroku

Ce document explique comment déployer l'application MCP sur Heroku.

## Prérequis

- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) installé
- [Git](https://git-scm.com/) installé
- Compte Heroku actif
- Python 3.11 ou supérieur

## Préparation au déploiement

1. **Configuration initiale**

   ```bash
   # Cloner le dépôt (si ce n'est pas déjà fait)
   git clone https://github.com/votrecompte/mcp.git
   cd mcp
   
   # Se connecter à Heroku
   heroku login
   ```

2. **Utiliser les scripts de configuration automatique**

   ```bash
   # Rendre les scripts exécutables
   chmod +x setup_heroku.sh setup_mongodb_heroku.sh verify_heroku_setup.sh
   
   # Exécuter le script de configuration Heroku
   ./setup_heroku.sh
   
   # Configurer MongoDB pour Heroku
   ./setup_mongodb_heroku.sh
   
   # Vérifier la configuration
   ./verify_heroku_setup.sh
   ```

## Déploiement manuel (si nécessaire)

1. **Créer une application Heroku**

   ```bash
   heroku create mcp-app --region eu
   ```

2. **Configurer les buildpacks**

   ```bash
   heroku buildpacks:add heroku/python
   ```

3. **Ajouter les addons nécessaires**

   ```bash
   # MongoDB
   heroku addons:create mongolab:sandbox
   
   # Redis (si nécessaire)
   heroku addons:create heroku-redis:mini --region eu
   ```

4. **Configurer les variables d'environnement**

   Vous pouvez soit les définir manuellement, soit utiliser le fichier .env :

   ```bash
   # Manuellement
   heroku config:set OPENAI_API_KEY=votre_clé
   heroku config:set ENVIRONMENT=production
   
   # Ou en utilisant le fichier .env
   cat .env | xargs heroku config:set
   ```

5. **Pousser le code vers Heroku**

   ```bash
   git push heroku main
   ```

## Surveillance et maintenance

1. **Vérifier les logs**

   ```bash
   heroku logs --tail
   ```

2. **Ouvrir l'application**

   ```bash
   heroku open
   ```

3. **Vérifier l'état des processus**

   ```bash
   heroku ps
   ```

4. **Redémarrer l'application si nécessaire**

   ```bash
   heroku restart
   ```

## Dépannage

### Erreur de build

Si vous rencontrez des erreurs lors du build :

```bash
heroku builds:output
```

### Problèmes de dépendances

Vérifiez que toutes les dépendances sont correctement listées dans `requirements.txt`.

### Problèmes de connexion à MongoDB

Vérifiez que la variable d'environnement `MONGODB_URI` est correctement configurée :

```bash
heroku config:get MONGODB_URI
```

### Libérer de l'espace dans le slug

Si votre slug est trop volumineux, utilisez `.slugignore` pour exclure les fichiers non nécessaires.

## Mise à jour de l'application

Pour mettre à jour l'application après des modifications locales :

```bash
git add .
git commit -m "Description des modifications"
git push heroku main
``` 