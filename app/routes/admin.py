# app/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.db import get_prod_database, get_db_summary, list_collections, count_documents, get_sample_documents
from motor.core import AgnosticDatabase, AgnosticCollection
from typing import List, Dict, Any

router = APIRouter(prefix="/admin", tags=["Administration"])

@router.get(
    "/db/summary",
    summary="Résumé de la base de données de production",
    description="Affiche un résumé des collections et documents dans la base de données de production."
)
async def get_database_summary():
    """Obtenir un résumé de la base de données de production."""
    db = await get_prod_database()
    return await get_db_summary(db)

@router.get(
    "/db/collections",
    summary="Liste des collections",
    description="Affiche la liste des collections dans la base de données de production."
)
async def get_collections():
    """Obtenir la liste des collections dans la base de données de production."""
    db = await get_prod_database()
    collections = await list_collections(db)
    return {"collections": collections}

@router.get(
    "/db/collections/{collection_name}",
    summary="Détails d'une collection",
    description="Affiche le nombre de documents et un échantillon des documents dans une collection."
)
async def get_collection_details(collection_name: str, limit: int = 5):
    """Obtenir les détails d'une collection spécifique."""
    db = await get_prod_database()
    
    # Vérifier si la collection existe
    collections = await list_collections(db)
    if collection_name not in collections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' non trouvée."
        )
    
    collection = db[collection_name]
    count = await count_documents(collection)
    sample = await get_sample_documents(collection, limit)
    
    return {
        "collection": collection_name,
        "count": count,
        "sample": sample
    } 