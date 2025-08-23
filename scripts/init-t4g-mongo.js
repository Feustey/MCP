// MongoDB Initialization Script for Token4Good (T4G)

print('🚀 Initializing Token4Good MongoDB Database...');

// Switch to T4G database
db = db.getSiblingDB('token4good');

// Create collections
db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['user_id', 'username', 'email'],
      properties: {
        user_id: { bsonType: 'string' },
        username: { bsonType: 'string' },
        email: { bsonType: 'string' },
        total_tokens_earned: { bsonType: 'int', minimum: 0 },
        total_tokens_spent: { bsonType: 'int', minimum: 0 },
        user_level: { enum: ['contributeur', 'mentor', 'expert'] },
        skills: { bsonType: 'array' },
        reputation_score: { bsonType: 'double', minimum: 0, maximum: 1 }
      }
    }
  }
});

db.createCollection('transactions', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['id', 'user_id', 'action_type'],
      properties: {
        id: { bsonType: 'string' },
        user_id: { bsonType: 'string' },
        action_type: { enum: ['mentoring', 'code_review', 'documentation', 'support_technique', 'parrainage', 'contribution_communautaire'] },
        tokens_earned: { bsonType: 'int', minimum: 0 },
        tokens_spent: { bsonType: 'int', minimum: 0 },
        impact_score: { bsonType: 'double', minimum: 0 }
      }
    }
  }
});

db.createCollection('services');
db.createCollection('bookings');
db.createCollection('mentoring_sessions');

// Create indexes for performance
db.users.createIndex({ user_id: 1 }, { unique: true });
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ username: 1 });
db.users.createIndex({ user_level: 1 });
db.users.createIndex({ total_tokens_earned: -1 });

db.transactions.createIndex({ id: 1 }, { unique: true });
db.transactions.createIndex({ user_id: 1 });
db.transactions.createIndex({ action_type: 1 });
db.transactions.createIndex({ timestamp: -1 });

db.services.createIndex({ id: 1 }, { unique: true });
db.services.createIndex({ provider_id: 1 });
db.services.createIndex({ category: 1 });
db.services.createIndex({ is_active: 1 });

db.bookings.createIndex({ id: 1 }, { unique: true });
db.bookings.createIndex({ client_id: 1 });
db.bookings.createIndex({ provider_id: 1 });
db.bookings.createIndex({ status: 1 });

db.mentoring_sessions.createIndex({ id: 1 }, { unique: true });
db.mentoring_sessions.createIndex({ mentor_id: 1 });
db.mentoring_sessions.createIndex({ mentee_id: 1 });
db.mentoring_sessions.createIndex({ status: 1 });

// Insert sample data
print('📊 Inserting sample data...');

// Sample services
db.services.insertMany([
  {
    id: 'lightning_mastery_001',
    name: 'Lightning Network Mastery',
    description: 'Accompagnement personnalisé sur la gestion de nœuds Lightning',
    category: 'technical_excellence',
    provider_id: 'system',
    token_cost: 50,
    estimated_duration: '1h',
    tags: ['lightning-network', 'bitcoin'],
    is_active: true,
    created_at: new Date()
  },
  {
    id: 'dazbox_setup_001',
    name: 'DazBox Setup Pro',
    description: 'Installation et optimisation guidée DazBox',
    category: 'technical_excellence',
    provider_id: 'system',
    token_cost: 75,
    estimated_duration: '1.5h',
    tags: ['dazbox', 'installation'],
    is_active: true,
    created_at: new Date()
  },
  {
    id: 'business_consultation_001',
    name: 'Bitcoin Business Development',
    description: 'Stratégies d\'intégration Lightning pour entreprises',
    category: 'business_growth',
    provider_id: 'system',
    token_cost: 100,
    estimated_duration: '2h',
    tags: ['business', 'strategy'],
    is_active: true,
    created_at: new Date()
  }
]);

// Sample expert user
db.users.insertOne({
  user_id: 'expert_demo_001',
  username: 'Lightning_Master',
  email: 'expert@dazno.de',
  total_tokens_earned: 2500,
  total_tokens_spent: 800,
  user_level: 'expert',
  skills: ['lightning-network', 'bitcoin', 'dazbox', 'business-development'],
  interests: ['mentoring', 'innovation'],
  reputation_score: 0.95,
  created_at: new Date(),
  last_activity: new Date()
});

print('✅ Token4Good MongoDB initialized successfully!');
print('📊 Collections created: users, transactions, services, bookings, mentoring_sessions');
print('🔍 Indexes created for optimal performance');
print('📝 Sample data inserted');
print('🎯 Ready for Token4Good API connection!');