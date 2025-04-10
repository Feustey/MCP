from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from src.auth.jwt import get_current_user
from src.auth.models import User
from src.db.mongo import get_database
from motor.core import AgnosticDatabase

# Création du router
router = APIRouter(
    prefix="/nodes",
    tags=["Nodes"],
    responses={
        401: {"description": "Non authentifié"},
        403: {"description": "Accès refusé"},
        429: {"description": "Trop de requêtes"},
        500: {"description": "Erreur serveur"}
    }
)

# Constante pour le nom de la collection MongoDB
NODE_COLLECTION = "nodes"

class NodeBase(BaseModel):
    """
    Modèle de base pour un nœud Lightning
    """
    pubkey: str = Field(..., description="Clé publique du nœud")
    alias: Optional[str] = Field(None, description="Alias du nœud")
    color: Optional[str] = Field(None, description="Couleur du nœud")
    capacity: Optional[float] = Field(None, description="Capacité totale en BTC")
    channels: Optional[int] = Field(None, description="Nombre de canaux")
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class NodeCreate(NodeBase):
    """
    Modèle pour la création d'un nœud
    """
    pass

class NodeUpdate(NodeBase):
    """
    Modèle pour la mise à jour d'un nœud
    """
    pubkey: Optional[str] = None
    last_updated: Optional[datetime] = None

class NodeInDB(NodeBase):
    """
    Modèle pour un nœud en base de données
    """
    id: str = Field(..., description="Identifiant unique du nœud")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

@router.post(
    "/",
    response_model=NodeInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouveau nœud",
    description="Ajoute un nouveau nœud Lightning à la base de données."
)
async def create_node(
    node: NodeCreate = Body(...),
    db: AgnosticDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Crée un nouveau nœud Lightning dans la collection.
    """
    # Vérifier si un nœud avec la même pubkey existe déjà
    existing_node = await db[NODE_COLLECTION].find_one({"pubkey": node.pubkey})
    if existing_node:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Un nœud avec la pubkey {node.pubkey} existe déjà."
        )

    # Convertir le modèle Pydantic en dictionnaire pour MongoDB
    node_dict = node.dict()
    node_dict["created_at"] = datetime.utcnow()
    node_dict["updated_at"] = datetime.utcnow()

    # Insérer le document dans la collection
    insert_result = await db[NODE_COLLECTION].insert_one(node_dict)
    created_node = await db[NODE_COLLECTION].find_one({"_id": insert_result.inserted_id})

    if created_node:
        return NodeInDB(**created_node)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du nœud."
        )

@router.get(
    "/",
    response_model=List[NodeInDB],
    summary="Liste des nœuds",
    description="Récupère la liste de tous les nœuds Lightning."
)
async def list_nodes(
    skip: int = Query(0, description="Nombre de nœuds à sauter"),
    limit: int = Query(10, description="Nombre maximum de nœuds à retourner"),
    db: AgnosticDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère la liste des nœuds Lightning avec pagination.
    """
    nodes = await db[NODE_COLLECTION].find().skip(skip).limit(limit).to_list(length=limit)
    return [NodeInDB(**node) for node in nodes]

@router.get(
    "/{node_id}",
    response_model=NodeInDB,
    summary="Détails d'un nœud",
    description="Récupère les détails d'un nœud Lightning spécifique."
)
async def get_node(
    node_id: str,
    db: AgnosticDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les détails d'un nœud Lightning.
    """
    node = await db[NODE_COLLECTION].find_one({"_id": node_id})
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nœud avec l'ID {node_id} non trouvé."
        )
    return NodeInDB(**node)

@router.put(
    "/{node_id}",
    response_model=NodeInDB,
    summary="Mettre à jour un nœud",
    description="Met à jour les informations d'un nœud Lightning."
)
async def update_node(
    node_id: str,
    node_update: NodeUpdate = Body(...),
    db: AgnosticDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour les informations d'un nœud Lightning.
    """
    # Vérifier si le nœud existe
    existing_node = await db[NODE_COLLECTION].find_one({"_id": node_id})
    if not existing_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nœud avec l'ID {node_id} non trouvé."
        )

    # Préparer les données de mise à jour
    update_data = node_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()

    # Effectuer la mise à jour
    await db[NODE_COLLECTION].update_one(
        {"_id": node_id},
        {"$set": update_data}
    )

    # Récupérer le nœud mis à jour
    updated_node = await db[NODE_COLLECTION].find_one({"_id": node_id})
    return NodeInDB(**updated_node)

@router.delete(
    "/{node_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un nœud",
    description="Supprime un nœud Lightning de la base de données."
)
async def delete_node(
    node_id: str,
    db: AgnosticDatabase = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Supprime un nœud Lightning.
    """
    # Vérifier si le nœud existe
    existing_node = await db[NODE_COLLECTION].find_one({"_id": node_id})
    if not existing_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nœud avec l'ID {node_id} non trouvé."
        )

    # Supprimer le nœud
    await db[NODE_COLLECTION].delete_one({"_id": node_id})
    return None 