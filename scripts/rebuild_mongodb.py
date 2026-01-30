#!/usr/bin/env python3
"""
Reconstruire la base MongoDB from scratch (solution 3).
Drop de la base mcp_prod puis recréation des collections et index
comme mongo-init.js. Utilisable avec MongoDB Runway / Atlas / local.

Usage:
  export MONGO_URL="mongodb+srv://user:pass@host/db"   # ou MONGODB_ATLAS_URL
  python scripts/rebuild_mongodb.py

  # Ou avec confirmation explicite (évite drop accidentel)
  python scripts/rebuild_mongodb.py --force
"""

import os
import sys

# Dépendance projet
try:
    from pymongo import MongoClient
except ImportError:
    print("❌ pymongo requis: pip install pymongo")
    sys.exit(1)

# Nom de la base (aligné mongo-init.js et config)
DB_NAME = os.environ.get("MONGODB_DATABASE") or os.environ.get("MONGO_NAME") or "mcp_prod"

# Schémas de validation (alignés sur mongo-init.js)
COLLECTIONS = {
    "nodes": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["node_id", "created_at"],
                "properties": {
                    "node_id": {"bsonType": "string"},
                    "created_at": {"bsonType": "date"},
                    "pubkey": {"bsonType": "string"},
                    "alias": {"bsonType": "string"},
                    "capacity": {"bsonType": ["int", "long"]},
                },
            }
        }
    },
    "channels": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["channel_id", "node_id", "created_at"],
                "properties": {
                    "channel_id": {"bsonType": "string"},
                    "node_id": {"bsonType": "string"},
                    "created_at": {"bsonType": "date"},
                },
            }
        }
    },
    "policies": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "properties": {
                    "channel_id": {"bsonType": "string"},
                    "applied_at": {"bsonType": "date"},
                    "base_fee_msat": {"bsonType": ["int", "long"]},
                    "fee_rate_ppm": {"bsonType": ["int", "long"]},
                },
            }
        }
    },
    "metrics": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "properties": {
                    "node_id": {"bsonType": "string"},
                    "timestamp": {"bsonType": "date"},
                },
            }
        }
    },
    "decisions": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "properties": {
                    "node_id": {"bsonType": "string"},
                    "channel_id": {"bsonType": "string"},
                    "decision_type": {"bsonType": "string"},
                    "created_at": {"bsonType": "date"},
                },
            }
        }
    },
    "macaroons": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["id", "name", "service"],
                "properties": {
                    "id": {"bsonType": "string"},
                    "name": {"bsonType": "string"},
                    "service": {"bsonType": "string"},
                    "macaroon": {"bsonType": "string"},
                    "created_at": {"bsonType": "date"},
                    "revoked": {"bsonType": "bool"},
                },
            }
        }
    },
}

# Indexes (clés + options) par collection
INDEXES = {
    "nodes": [
        ({"node_id": 1}, {"unique": True, "name": "idx_node_id"}),
        ({"created_at": -1}, {"name": "idx_created_at"}),
        ({"pubkey": 1}, {"name": "idx_pubkey"}),
    ],
    "channels": [
        ({"channel_id": 1}, {"unique": True, "name": "idx_channel_id"}),
        ({"node_id": 1}, {"name": "idx_node_id"}),
        ({"created_at": -1}, {"name": "idx_created_at"}),
        ({"node_id": 1, "created_at": -1}, {"name": "idx_node_created"}),
    ],
    "policies": [
        ({"channel_id": 1}, {"name": "idx_channel_id"}),
        ({"applied_at": -1}, {"name": "idx_applied_at"}),
        ({"channel_id": 1, "applied_at": -1}, {"name": "idx_channel_applied"}),
    ],
    "metrics": [
        ({"node_id": 1, "timestamp": -1}, {"name": "idx_node_timestamp"}),
        ({"timestamp": -1}, {"name": "idx_timestamp"}),
        ({"node_id": 1}, {"name": "idx_node_id"}),
    ],
    "decisions": [
        ({"node_id": 1, "created_at": -1}, {"name": "idx_node_created"}),
        ({"channel_id": 1, "created_at": -1}, {"name": "idx_channel_created"}),
        ({"decision_type": 1}, {"name": "idx_decision_type"}),
        ({"created_at": -1}, {"name": "idx_created_at"}),
    ],
    "macaroons": [
        ({"id": 1}, {"unique": True, "name": "idx_macaroon_id"}),
        ({"name": 1, "service": 1}, {"name": "idx_name_service"}),
        ({"revoked": 1}, {"name": "idx_revoked"}),
        ({"created_at": -1}, {"name": "idx_created_at"}),
    ],
}


def get_mongo_url() -> str:
    url = (
        os.environ.get("MONGO_URL")
        or os.environ.get("MONGODB_ATLAS_URL")
        or os.environ.get("MONGODB_URL")
    )
    if not url:
        print("❌ Définir MONGO_URL, MONGODB_ATLAS_URL ou MONGODB_URL")
        sys.exit(1)
    return url


def main():
    force = "--force" in sys.argv or "-f" in sys.argv
    url = get_mongo_url()

    print("🚀 Reconstruire la base MongoDB (solution 3 – from scratch)")
    print(f"   Base: {DB_NAME}")
    if not force:
        print("   ⚠️  Toutes les données seront supprimées.")
        r = input("   Continuer ? [y/N] ").strip().lower()
        if r != "y":
            print("   Annulé.")
            sys.exit(0)

    client = MongoClient(url, serverSelectionTimeoutMS=10000)
    try:
        client.admin.command("ping")
    except Exception as e:
        print(f"❌ Connexion MongoDB impossible: {e}")
        sys.exit(1)

    db = client[DB_NAME]

    # 1) Drop
    print(f"\n📦 Suppression de la base '{DB_NAME}'...")
    client.drop_database(DB_NAME)
    print("   OK.")

    # 2) Collections + validators
    print("\n📦 Création des collections avec validation...")
    for name, opts in COLLECTIONS.items():
        db.create_collection(name, **opts)
        print(f"   {name}")

    # 3) Indexes
    print("\n🔍 Création des index...")
    for coll_name, index_list in INDEXES.items():
        coll = db[coll_name]
        for keys, options in index_list:
            coll.create_index(keys, **options)
        print(f"   {coll_name}: {len(index_list)} index")

    print("\n✅ Base reconstruite avec succès.")
    print("📊 Collections: nodes, channels, policies, metrics, decisions, macaroons")
    print("🎯 Prête pour MCP v1.0")


if __name__ == "__main__":
    main()
