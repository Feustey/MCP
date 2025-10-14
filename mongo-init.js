// mongo-init.js
// Script d'initialisation pour MongoDB
// Exécuté automatiquement au premier démarrage du container

print('🚀 Initialisation de MongoDB pour MCP...');

// Se connecter à la base de données
db = db.getSiblingDB('mcp_prod');

print('📦 Création des collections avec validation...');

// Collection: nodes
db.createCollection('nodes', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["node_id", "created_at"],
      properties: {
        node_id: { 
          bsonType: "string",
          description: "ID unique du nœud Lightning"
        },
        created_at: { 
          bsonType: "date",
          description: "Date de création"
        },
        pubkey: { bsonType: "string" },
        alias: { bsonType: "string" },
        capacity: { bsonType: ["int", "long"] }
      }
    }
  }
});

// Collection: channels
db.createCollection('channels', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["channel_id", "node_id", "created_at"],
      properties: {
        channel_id: { 
          bsonType: "string",
          description: "ID unique du canal"
        },
        node_id: { 
          bsonType: "string",
          description: "ID du nœud propriétaire"
        },
        created_at: { 
          bsonType: "date",
          description: "Date de création"
        }
      }
    }
  }
});

// Collection: policies (politiques de fees)
db.createCollection('policies', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      properties: {
        channel_id: { bsonType: "string" },
        applied_at: { bsonType: "date" },
        base_fee_msat: { bsonType: ["int", "long"] },
        fee_rate_ppm: { bsonType: ["int", "long"] }
      }
    }
  }
});

// Collection: metrics
db.createCollection('metrics', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      properties: {
        node_id: { bsonType: "string" },
        timestamp: { bsonType: "date" }
      }
    }
  }
});

// Collection: decisions
db.createCollection('decisions', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      properties: {
        node_id: { bsonType: "string" },
        channel_id: { bsonType: "string" },
        decision_type: { bsonType: "string" },
        created_at: { bsonType: "date" }
      }
    }
  }
});

// Collection: macaroons (authentification)
db.createCollection('macaroons', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id", "name", "service"],
      properties: {
        id: { bsonType: "string" },
        name: { bsonType: "string" },
        service: { bsonType: "string" },
        macaroon: { bsonType: "string" },
        created_at: { bsonType: "date" },
        revoked: { bsonType: "bool" }
      }
    }
  }
});

print('🔍 Création des indexes pour performance...');

// Indexes pour nodes
db.nodes.createIndex({ "node_id": 1 }, { unique: true, name: "idx_node_id" });
db.nodes.createIndex({ "created_at": -1 }, { name: "idx_created_at" });
db.nodes.createIndex({ "pubkey": 1 }, { name: "idx_pubkey" });

// Indexes pour channels
db.channels.createIndex({ "channel_id": 1 }, { unique: true, name: "idx_channel_id" });
db.channels.createIndex({ "node_id": 1 }, { name: "idx_node_id" });
db.channels.createIndex({ "created_at": -1 }, { name: "idx_created_at" });
db.channels.createIndex({ "node_id": 1, "created_at": -1 }, { name: "idx_node_created" });

// Indexes pour policies
db.policies.createIndex({ "channel_id": 1 }, { name: "idx_channel_id" });
db.policies.createIndex({ "applied_at": -1 }, { name: "idx_applied_at" });
db.policies.createIndex({ "channel_id": 1, "applied_at": -1 }, { name: "idx_channel_applied" });

// Indexes pour metrics
db.metrics.createIndex({ "node_id": 1, "timestamp": -1 }, { name: "idx_node_timestamp" });
db.metrics.createIndex({ "timestamp": -1 }, { name: "idx_timestamp" });
db.metrics.createIndex({ "node_id": 1 }, { name: "idx_node_id" });

// Indexes pour decisions
db.decisions.createIndex({ "node_id": 1, "created_at": -1 }, { name: "idx_node_created" });
db.decisions.createIndex({ "channel_id": 1, "created_at": -1 }, { name: "idx_channel_created" });
db.decisions.createIndex({ "decision_type": 1 }, { name: "idx_decision_type" });
db.decisions.createIndex({ "created_at": -1 }, { name: "idx_created_at" });

// Indexes pour macaroons
db.macaroons.createIndex({ "id": 1 }, { unique: true, name: "idx_macaroon_id" });
db.macaroons.createIndex({ "name": 1, "service": 1 }, { name: "idx_name_service" });
db.macaroons.createIndex({ "revoked": 1 }, { name: "idx_revoked" });
db.macaroons.createIndex({ "created_at": -1 }, { name: "idx_created_at" });

print('✅ MongoDB initialisé avec succès !');
print('📊 Collections créées: nodes, channels, policies, metrics, decisions, macaroons');
print('🔍 Indexes créés pour optimisation des requêtes');
print('');
print('🎯 Base de données prête pour MCP v1.0');

