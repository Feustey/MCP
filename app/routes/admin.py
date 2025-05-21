# app/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from app.db import get_prod_database, get_db_summary, list_collections, count_documents, get_sample_documents
from motor.core import AgnosticDatabase, AgnosticCollection
from typing import List, Dict, Any
from app.auth import verify_jwt_and_get_tenant

router = APIRouter(prefix="/admin", tags=["Administration"])

@router.get(
    "/db/summary",
    summary="Résumé de la base de données de production",
    description="Affiche un résumé des collections et documents dans la base de données de production."
)
async def get_database_summary(authorization: str = Header(..., alias="Authorization")):
    tenant_id = verify_jwt_and_get_tenant(authorization)
    db = await get_prod_database()
    return await get_db_summary(db, tenant_id=tenant_id)

@router.get(
    "/db/collections",
    summary="Liste des collections",
    description="Affiche la liste des collections dans la base de données de production."
)
async def get_collections(authorization: str = Header(..., alias="Authorization")):
    tenant_id = verify_jwt_and_get_tenant(authorization)
    db = await get_prod_database()
    collections = await list_collections(db, tenant_id=tenant_id)
    return {"collections": collections}

@router.get(
    "/db/collections/{collection_name}",
    summary="Détails d'une collection",
    description="Affiche le nombre de documents et un échantillon des documents dans une collection."
)
async def get_collection_details(collection_name: str, limit: int = 5, authorization: str = Header(..., alias="Authorization")):
    tenant_id = verify_jwt_and_get_tenant(authorization)
    db = await get_prod_database()
    
    # Vérifier si la collection existe
    collections = await list_collections(db, tenant_id=tenant_id)
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