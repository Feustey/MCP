// Script d'initialisation MongoDB pour MCP Production
// Créé automatiquement le Dim 25 mai 2025 15:27:05 CEST

db = db.getSiblingDB('mcp_prod');

// Créer l'utilisateur applicatif
db.createUser({
  user: 'mcp_admin',
  pwd: 'VwSrcnNI8i5m2sim',
  roles: [
    { role: 'readWrite', db: 'mcp_prod' },
    { role: 'dbAdmin', db: 'mcp_prod' }
  ]
});

// Créer les collections de base
db.createCollection('nodes');
db.createCollection('metrics');
db.createCollection('reports');
db.createCollection('actions');

// Créer les index de base
db.nodes.createIndex({ "public_key": 1 }, { unique: true });
db.metrics.createIndex({ "timestamp": 1 });
db.reports.createIndex({ "created_at": 1 });

print('✓ Base de données MCP initialisée');
