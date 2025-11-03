# 🚀 Quick Start - RAG Modèle Léger

## Installation Express (5 minutes)

\`\`\`bash
cd /Users/stephanecourant/Documents/DAZ/MCP/MCP

# 1. Configuration
cp env.hostinger.example .env
nano .env  # Remplir: SECRET_KEY, ENCRYPTION_KEY, MONGODB_PASSWORD, REDIS_PASSWORD, LNBITS_*

# 2. Déploiement
./deploy_rag_production.sh

# 3. Validation
curl http://localhost:8000/health
docker exec mcp-ollama ollama list
\`\`\`

## Changements Clés

- **Modèle:** llama3:8b-instruct (au lieu de 70b)
- **RAM:** ~6 GB (au lieu de ~45 GB)
- **Vitesse:** 2-5s (au lieu de 5-15s)
- **Coût:** ~$50-100/mois (au lieu de $200-400)

## Documentation Complète

- **Guide détaillé:** [GUIDE_DEPLOIEMENT_RAG_LEGER.md](GUIDE_DEPLOIEMENT_RAG_LEGER.md)
- **Changements:** [CHANGEMENTS_MODELE_LEGER.md](CHANGEMENTS_MODELE_LEGER.md)
- **Status:** [DEPLOY_READY_20OCT2025.md](DEPLOY_READY_20OCT2025.md)

## Support

\`\`\`bash
# Logs
docker-compose -f docker-compose.hostinger.yml logs -f

# Restart
docker-compose -f docker-compose.hostinger.yml restart

# Status
docker-compose -f docker-compose.hostinger.yml ps
\`\`\`
