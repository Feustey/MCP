# app/routes/nodes.py
from fastapi import APIRouter, Depends, HTTPException, status, Body
from motor.core import AgnosticDatabase, AgnosticCollection
from app.db import get_database, get_node_collection
from app.models import NodeInDB, NodeCreate, NodeUpdate
from typing import List
from bson import ObjectId
from datetime import datetime

# Création d'un routeur spécifique pour les nodes
# prefix='/nodes' -> toutes les routes ici commenceront par /nodes
# tags=['Nodes'] -> regroupe ces routes dans la doc Swagger UI
router = APIRouter(prefix="/nodes", tags=["Nodes"])

# Constante pour le nom de la collection MongoDB
NODE_COLLECTION = "nodes"

@router.post(
    "/",
    response_model=NodeInDB, # Le modèle de réponse attendu (inclut l'ID)
    status_code=status.HTTP_201_CREATED, # Code HTTP pour une création réussie
    summary="Créer un nouveau node",
    description="Ajoute un nouveau node Lightning à la base de données."
)
async def create_node(
    node: NodeCreate = Body(...), # Récupère les données du corps de la requête et valide avec NodeCreate
    db: AgnosticDatabase = Depends(get_database) # Injecte la dépendance de base de données
):
    """Crée un nouveau node Lightning dans la collection.

    - **node**: Données du node à créer.
    - **db**: Instance de la base de données injectée.
    """
    # Vérifier si un node avec la même pubkey existe déjà
    existing_node = await db[NODE_COLLECTION].find_one({"pubkey": node.pubkey})
    if existing_node:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Un node avec la pubkey {node.pubkey} existe déjà."
        )

    # Convertir le modèle Pydantic en dictionnaire pour MongoDB
    node_dict = node.dict()
    # Ajouter la date de création/mise à jour
    node_dict["last_updated"] = datetime.utcnow()

    # Insérer le document dans la collection
    insert_result = await db[NODE_COLLECTION].insert_one(node_dict)

    # Vérifier si l'insertion a réussi et récupérer le document inséré
    created_node = await db[NODE_COLLECTION].find_one({"_id": insert_result.inserted_id})

    if created_node:
        return created_node # Retourne le node créé, validé par NodeInDB
    else:
        # Cela ne devrait théoriquement pas arriver si l'insertion réussit
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du node après insertion."
        )

@router.get(
    "/",
    response_model=List[NodeInDB], # Attend une liste de nodes
    summary="Lister tous les nodes",
    description="Récupère une liste de tous les nodes Lightning enregistrés."
)
async def list_nodes(
    db: AgnosticDatabase = Depends(get_database),
    limit: int = 100 # Paramètre de requête optionnel pour limiter le nombre de résultats
):
    """Récupère une liste de nodes depuis la collection.

    - **db**: Instance de la base de données injectée.
    - **limit**: Nombre maximum de nodes à retourner.
    """
    nodes_cursor = db[NODE_COLLECTION].find().limit(limit)
    nodes = await nodes_cursor.to_list(length=limit) # Exécute la requête
    return nodes # FastAPI s'occupe de la sérialisation via response_model

@router.get(
    "/{node_id}", # Paramètre de chemin pour l'ID ou la pubkey
    response_model=NodeInDB,
    summary="Obtenir un node spécifique",
    description="Récupère les informations d'un node par son ID MongoDB ou sa clé publique.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Node non trouvé"}
    }
)
async def get_node(
    node_id: str, # ID ou pubkey passé dans l'URL
    db: AgnosticDatabase = Depends(get_database)
):
    """Récupère un node par son ID ou sa pubkey.

    - **node_id**: ID MongoDB (string) ou Pubkey (string) du node.
    - **db**: Instance de la base de données injectée.
    """
    # Essayer de trouver par ObjectId d'abord
    if ObjectId.is_valid(node_id):
        node = await db[NODE_COLLECTION].find_one({"_id": ObjectId(node_id)})
        if node:
            return node

    # Si non trouvé par ID ou si ce n'est pas un ID valide, essayer par pubkey
    node = await db[NODE_COLLECTION].find_one({"pubkey": node_id})
    if node:
        return node

    # Si toujours pas trouvé, lever une exception 404
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Node avec ID ou Pubkey '{node_id}' non trouvé."
    )

@router.patch(
    "/{node_id}",
    response_model=NodeInDB,
    summary="Mettre à jour un node",
    description="Met à jour partiellement les informations d'un node existant par son ID ou sa pubkey.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Node non trouvé"}
    }
)
async def update_node(
    node_id: str,
    node_update: NodeUpdate = Body(...), # Données de mise à jour partielles
    db: AgnosticDatabase = Depends(get_database)
):
    """Met à jour un node existant.

    - **node_id**: ID MongoDB ou Pubkey du node à mettre à jour.
    - **node_update**: Champs à mettre à jour.
    - **db**: Instance de la base de données injectée.
    """
    # Créer le dictionnaire de mise à jour en excluant les valeurs None
    # et en ajoutant la date de mise à jour
    update_data = node_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune donnée fournie pour la mise à jour."
        )

    update_data["last_updated"] = datetime.utcnow()

    # Essayer de trouver et mettre à jour par ObjectId
    if ObjectId.is_valid(node_id):
        result = await db[NODE_COLLECTION].update_one(
            {"_id": ObjectId(node_id)},
            {"$set": update_data}
        )
        if result.modified_count == 1:
            updated_node = await db[NODE_COLLECTION].find_one({"_id": ObjectId(node_id)})
            return updated_node

    # Si non trouvé ou non mis à jour par ID, essayer par pubkey
    result = await db[NODE_COLLECTION].update_one(
        {"pubkey": node_id},
        {"$set": update_data}
    )
    if result.modified_count == 1:
        updated_node = await db[NODE_COLLECTION].find_one({"pubkey": node_id})
        return updated_node

    # Si le node n'a pas été trouvé ni par ID ni par pubkey
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Node avec ID ou Pubkey '{node_id}' non trouvé pour la mise à jour."
    )

@router.delete(
    "/{node_id}",
    status_code=status.HTTP_204_NO_CONTENT, # Pas de contenu retourné en cas de succès
    summary="Supprimer un node",
    description="Supprime un node de la base de données par son ID ou sa pubkey.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Node non trouvé"}
    }
)
async def delete_node(
    node_id: str,
    db: AgnosticDatabase = Depends(get_database)
):
    """Supprime un node par son ID ou sa pubkey.

    - **node_id**: ID MongoDB ou Pubkey du node à supprimer.
    - **db**: Instance de la base de données injectée.
    """
    # Essayer de supprimer par ObjectId
    if ObjectId.is_valid(node_id):
        delete_result = await db[NODE_COLLECTION].delete_one({"_id": ObjectId(node_id)})
        if delete_result.deleted_count == 1:
            return # Succès, retourne 204 No Content

    # Si non supprimé par ID, essayer par pubkey
    delete_result = await db[NODE_COLLECTION].delete_one({"pubkey": node_id})
    if delete_result.deleted_count == 1:
        return # Succès, retourne 204 No Content

    # Si le node n'a pas été trouvé pour la suppression
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Node avec ID ou Pubkey '{node_id}' non trouvé pour la suppression."
    ) 