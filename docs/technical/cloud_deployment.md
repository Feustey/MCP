# Déploiement Cloud du Projet MCP

## Prérequis
- Docker et Docker Compose installés sur la machine de déploiement (VM cloud, instance GCP/AWS, Railway, etc.)
- Accès réseau aux services nécessaires (API, base de données, monitoring)
- Variables d’environnement configurées (voir `.env`)

## Déploiement rapide
1. Cloner le repository MCP sur votre VM/instance cloud
2. Copier et adapter le fichier `.env` si besoin
3. Lancer le script de déploiement :
   ```bash
   ./scripts/deploy_cloud.sh
   ```
4. Vérifier que les services sont bien démarrés :
   ```bash
   docker compose ps
   ```

## Points d’adaptation pour le cloud
- Adapter `docker-compose.yml` pour utiliser des volumes cloud (S3, GCS, etc.) si besoin
- Ouvrir les ports nécessaires dans le firewall cloud (API, monitoring, etc.)
- Pour l’auto-update, intégrer [Watchtower](https://containrrr.dev/watchtower/) ou [Nomad](https://www.nomadproject.io/)
- Pour le monitoring, brancher Prometheus/Grafana sur les métriques exposées

## Bonnes pratiques
- Utiliser un provider cloud managé pour la base de données et le vector store (Pinecone, Weaviate Cloud, Qdrant Cloud…)
- Sécuriser l’accès à l’API (HTTPS, authentification JWT/OAuth2)
- Mettre en place des sauvegardes automatiques pour les données critiques

## Support
Pour toute question ou adaptation avancée, se référer à la documentation principale ou contacter l’équipe MCP. 