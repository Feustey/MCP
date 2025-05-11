// Script d'initialisation MongoDB pour MCP
// Ce script crée les collections et index nécessaires

db = db.getSiblingDB('mcp_db');

// Création des collections principales
db.createCollection('nodes');
db.createCollection('channels');
db.createCollection('fee_policies');
db.createCollection('decisions');
db.createCollection('metrics');
db.createCollection('rag_documents');
db.createCollection('system_logs');
db.createCollection('rollbacks');

// Collection pour les nœuds
db.nodes.createIndex({ "node_id": 1 }, { unique: true });
db.nodes.createIndex({ "alias": 1 });
db.nodes.createIndex({ "last_update": 1 });
db.nodes.createIndex({ "scores.overall": 1 });

// Collection pour les canaux
db.channels.createIndex({ "channel_id": 1 }, { unique: true });
db.channels.createIndex({ "short_channel_id": 1 });
db.channels.createIndex({ "node1_pub": 1 });
db.channels.createIndex({ "node2_pub": 1 });
db.channels.createIndex({ "status": 1 });
db.channels.createIndex({ "capacity": 1 });
db.channels.createIndex({ "last_update": 1 });

// Collection pour les politiques de frais
db.fee_policies.createIndex({ "channel_id": 1, "timestamp": 1 });
db.fee_policies.createIndex({ "node_id": 1 });
db.fee_policies.createIndex({ "applied": 1 });
db.fee_policies.createIndex({ "result": 1 });

// Collection pour les décisions
db.decisions.createIndex({ "decision_id": 1 }, { unique: true });
db.decisions.createIndex({ "node_id": 1 });
db.decisions.createIndex({ "channel_id": 1 });
db.decisions.createIndex({ "timestamp": 1 });
db.decisions.createIndex({ "decision_type": 1 });
db.decisions.createIndex({ "execution_status": 1 });

// Collection pour les métriques
db.metrics.createIndex({ "node_id": 1, "timestamp": 1 });
db.metrics.createIndex({ "channel_id": 1, "timestamp": 1 });
db.metrics.createIndex({ "metric_type": 1 });

// Collection pour les documents RAG
db.rag_documents.createIndex({ "source": 1 });
db.rag_documents.createIndex({ "metadata.related_node": 1 });
db.rag_documents.createIndex({ "metadata.created_at": 1 });
db.rag_documents.createIndex({ "metadata.type": 1 });

// Collection pour les logs système
db.system_logs.createIndex({ "timestamp": 1 });
db.system_logs.createIndex({ "level": 1 });
db.system_logs.createIndex({ "component": 1 });

// Collection pour les rollbacks
db.rollbacks.createIndex({ "rollback_id": 1 }, { unique: true });
db.rollbacks.createIndex({ "channel_id": 1 });
db.rollbacks.createIndex({ "timestamp": 1 });
db.rollbacks.createIndex({ "status": 1 });

// Création de la base de test
db = db.getSiblingDB('mcp_test_db');

// Reproduire les mêmes collections pour les tests
db.createCollection('nodes');
db.createCollection('channels');
db.createCollection('fee_policies');
db.createCollection('decisions');
db.createCollection('metrics');
db.createCollection('rag_documents');
db.createCollection('system_logs');
db.createCollection('rollbacks');

// Reproduire les mêmes index pour les tests
db.nodes.createIndex({ "node_id": 1 }, { unique: true });
db.channels.createIndex({ "channel_id": 1 }, { unique: true });
db.fee_policies.createIndex({ "channel_id": 1, "timestamp": 1 });
db.decisions.createIndex({ "decision_id": 1 }, { unique: true });
db.metrics.createIndex({ "node_id": 1, "timestamp": 1 });
db.rag_documents.createIndex({ "source": 1 });
db.system_logs.createIndex({ "timestamp": 1 });
db.rollbacks.createIndex({ "rollback_id": 1 }, { unique: true });

// Création de la base de simulation
db = db.getSiblingDB('mcp_simulation_db');

// Reproduire les mêmes collections pour la simulation
db.createCollection('nodes');
db.createCollection('channels');
db.createCollection('fee_policies');
db.createCollection('decisions');
db.createCollection('metrics');
db.createCollection('simulation_scenarios');
db.createCollection('simulation_results');

// Index spécifiques à la simulation
db.nodes.createIndex({ "node_id": 1 }, { unique: true });
db.channels.createIndex({ "channel_id": 1 }, { unique: true });
db.simulation_scenarios.createIndex({ "scenario_id": 1 }, { unique: true });
db.simulation_results.createIndex({ "run_id": 1 }, { unique: true });
db.simulation_results.createIndex({ "scenario_id": 1 });
db.simulation_results.createIndex({ "timestamp": 1 });

print("MongoDB initialization completed successfully"); 