// Script d'initialisation MongoDB pour MCP
// Dernière mise à jour: 7 janvier 2025

// Connexion à la base de données admin
db = db.getSiblingDB('admin');

// Création de l'utilisateur MCP
db.createUser({
  user: "mcp_user",
  pwd: "mcp_user_password_2025",
  roles: [
    {
      role: "readWrite",
      db: "mcp"
    }
  ]
});

// Connexion à la base de données MCP
db = db.getSiblingDB('mcp');

// Création des collections principales
db.createCollection('nodes');
db.createCollection('channels');
db.createCollection('metrics');
db.createCollection('optimizations');
db.createCollection('reports');
db.createCollection('simulations');

// Création des index pour optimiser les performances
db.nodes.createIndex({ "node_id": 1 }, { unique: true });
db.nodes.createIndex({ "alias": 1 });
db.nodes.createIndex({ "last_updated": -1 });

db.channels.createIndex({ "channel_id": 1 }, { unique: true });
db.channels.createIndex({ "node1_pub": 1 });
db.channels.createIndex({ "node2_pub": 1 });
db.channels.createIndex({ "capacity": -1 });

db.metrics.createIndex({ "node_id": 1, "timestamp": -1 });
db.metrics.createIndex({ "timestamp": -1 });

db.optimizations.createIndex({ "node_id": 1, "timestamp": -1 });
db.optimizations.createIndex({ "status": 1 });

db.reports.createIndex({ "node_id": 1, "created_at": -1 });
db.reports.createIndex({ "report_type": 1 });

db.simulations.createIndex({ "profile": 1, "timestamp": -1 });

// Insertion de données de test (optionnel)
db.nodes.insertOne({
  node_id: "test_node_001",
  alias: "Test Node",
  pub_key: "02testpubkey123456789",
  last_updated: new Date(),
  channels_count: 0,
  total_capacity: 0,
  avg_fee_rate: 0.001
});

print("✅ Base de données MCP initialisée avec succès");
