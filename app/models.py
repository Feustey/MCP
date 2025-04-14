from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any, Annotated
from bson import ObjectId
from datetime import datetime
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema, CoreSchema

# Classe utilitaire pour gérer les ObjectId de MongoDB dans Pydantic
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> ObjectId:
        if isinstance(v, ObjectId):
            return v
        if ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Any,
    ) -> CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

# Modèle Pydantic pour représenter un Node Lightning dans la base de données
# Ce modèle inclut l'_id généré par MongoDB
class NodeInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    alias: str = Field(..., min_length=1, max_length=50, description="Nom d'affichage du node")
    pubkey: str = Field(..., pattern=r"^[0-9a-fA-F]{66}$", description="Clé publique du node (hexadécimal, 66 caractères)")
    score: float = Field(..., ge=0, le=100, description="Score de qualité du node (0-100)")
    channels: int = Field(..., ge=0, description="Nombre de canaux ouverts")
    last_updated: Optional[datetime] = Field(None, description="Date de dernière mise à jour des informations")

    class Config:
        populate_by_name = True # Permet d'utiliser `_id` ou `id`
        arbitrary_types_allowed = True # Nécessaire pour PyObjectId
        json_encoders = {
            ObjectId: str, # Convertit ObjectId en string pour les réponses JSON
            datetime: lambda dt: dt.isoformat() # Formate les datetimes en ISO
        }
        json_schema_extra = {
            "example": {
                "_id": "60d5ecf1e4b0f8d9f3b1e3e1",
                "alias": "MonSuperNode",
                "pubkey": "02abcdef1234567890abcdef1234567890abcdef1234567890abcdef123456",
                "score": 95.7,
                "channels": 25,
                "last_updated": "2023-10-27T10:00:00Z"
            }
        }

# Modèle Pydantic pour la création d'un nouveau Node
# Pas besoin d'ID ici, car MongoDB le générera
# last_updated est aussi optionnel ou géré automatiquement
class NodeCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=50, description="Nom d'affichage du node")
    pubkey: str = Field(..., pattern=r"^[0-9a-fA-F]{66}$", description="Clé publique du node (hexadécimal, 66 caractères)")
    score: float = Field(..., ge=0, le=100, description="Score de qualité du node (0-100)")
    channels: int = Field(..., ge=0, description="Nombre de canaux ouverts")

    class Config:
        json_schema_extra = {
            "example": {
                "alias": "NouveauNode",
                "pubkey": "03fedcba9876543210fedcba9876543210fedcba9876543210fedcba987654",
                "score": 88.2,
                "channels": 10
            }
        }

# Modèle Pydantic pour la mise à jour partielle d'un Node (PATCH)
# Tous les champs sont optionnels
class NodeUpdate(BaseModel):
    alias: Optional[str] = Field(None, min_length=1, max_length=50, description="Nouveau nom d'affichage (optionnel)")
    score: Optional[float] = Field(None, ge=0, le=100, description="Nouveau score (optionnel)")
    channels: Optional[int] = Field(None, ge=0, description="Nouveau nombre de canaux (optionnel)")
    last_updated: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Date de mise à jour")

    class Config:
        json_schema_extra = {
            "example": {
                "alias": "NodeRenommé",
                "score": 91.0
            }
        } 