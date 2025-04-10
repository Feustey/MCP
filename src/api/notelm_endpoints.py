from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import os
import aiohttp
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création du router
router = APIRouter(
    prefix="/notelm",
    tags=["Notelm"],
    responses={
        401: {"description": "Non authentifié"},
        403: {"description": "Accès refusé"},
        429: {"description": "Trop de requêtes"},
        500: {"description": "Erreur serveur"}
    }
)

# Configuration Notelm
NOTELM_NOTEBOOK_ID = os.getenv("NOTELM_NOTEBOOK_ID", "6cfbfe60-3b64-4522-a867-229f55dd73b0")
NOTELM_BASE_URL = "https://notebooklm.google.com/api/v1"

class NotebookSection(BaseModel):
    """
    Modèle pour une section du notebook
    """
    title: str = Field(..., description="Titre de la section")
    content: str = Field(..., description="Contenu de la section")
    metadata: Dict = Field(..., description="Métadonnées de la section")
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Introduction au Lightning Network",
                "content": "Le Lightning Network est une solution de couche 2 pour Bitcoin...",
                "metadata": {
                    "last_modified": "2024-03-15T10:30:00Z",
                    "author": "Lightning Network Team",
                    "type": "lightning_notebook",
                    "source": "notebooklm",
                    "section_id": "section-123"
                }
            }
        }

class NotebookContent(BaseModel):
    """
    Modèle pour le contenu du notebook
    """
    sections: List[NotebookSection] = Field(..., description="Liste des sections du notebook")
    last_updated: datetime = Field(..., description="Date de dernière mise à jour")
    total_sections: int = Field(..., description="Nombre total de sections")

class LearningPath(BaseModel):
    """
    Modèle pour un parcours d'apprentissage
    """
    title: str = Field(..., description="Titre du parcours")
    description: str = Field(..., description="Description du parcours")
    sections: List[str] = Field(..., description="Liste des IDs des sections dans l'ordre")
    difficulty: str = Field(..., description="Niveau de difficulté (débutant, intermédiaire, avancé)")
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Devenir un expert Lightning Network",
                "description": "Un parcours complet pour maîtriser le Lightning Network",
                "sections": ["section-1", "section-2", "section-3"],
                "difficulty": "intermédiaire"
            }
        }

class NotelmConnector:
    """
    Connecteur pour l'API Notelm
    """
    def __init__(self, notebook_id: str):
        self.notebook_id = notebook_id
        self.base_url = NOTELM_BASE_URL
        self.logger = logging.getLogger(__name__)

    async def fetch_notebook_content(self) -> Dict[str, Any]:
        """
        Récupère le contenu du notebook depuis l'API Notelm
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/notebooks/{self.notebook_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"Erreur {response.status} lors de la récupération du contenu Notelm")
                        return {}
        except Exception as e:
            self.logger.error(f"Erreur de connexion à Notelm: {e}")
            return {}

    def parse_notebook_sections(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse les sections du notebook
        """
        sections = []
        for section in content.get("sections", []):
            parsed_section = {
                "title": section.get("title", ""),
                "content": section.get("content", ""),
                "metadata": {
                    "last_modified": section.get("lastModified"),
                    "author": section.get("author"),
                    "type": "lightning_notebook",
                    "source": "notebooklm",
                    "section_id": section.get("id")
                }
            }
            sections.append(parsed_section)
        return sections

# Instance du connecteur Notelm
notelm_connector = NotelmConnector(NOTELM_NOTEBOOK_ID)

@router.get("/sections", response_model=Dict[str, Any])
async def get_sections(
    tags: Optional[List[str]] = Query(None, description="Filtrer les sections par tags")
):
    """
    Récupère les sections du notebook Lightning Network.
    
    Cette endpoint permet d'accéder au contenu du notebook Lightning Network,
    avec possibilité de filtrer les sections par tags.
    
    - **tags**: Liste de tags pour filtrer les sections (optionnel)
    
    Returns:
        Dict: Liste des sections et leur nombre
    """
    try:
        content = await notelm_connector.fetch_notebook_content()
        sections = notelm_connector.parse_notebook_sections(content)
        
        # Filtrage par tags si spécifié
        if tags:
            filtered_sections = []
            for section in sections:
                section_tags = section.get("metadata", {}).get("tags", [])
                if any(tag in section_tags for tag in tags):
                    filtered_sections.append(section)
            sections = filtered_sections
        
        return {
            "sections": sections,
            "count": len(sections)
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des sections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/learning-paths", response_model=List[LearningPath])
async def get_learning_paths():
    """
    Récupère les parcours d'apprentissage disponibles.
    
    Cette endpoint fournit les différents parcours d'apprentissage
    pour maîtriser le Lightning Network.
    
    Returns:
        List[LearningPath]: Liste des parcours d'apprentissage
    """
    try:
        # Pour l'instant, retournons des données statiques
        # Dans une implémentation réelle, ces données viendraient de Notelm
        learning_paths = [
            {
                "title": "Débuter avec Lightning Network",
                "description": "Un parcours pour comprendre les bases du Lightning Network",
                "sections": ["section-1", "section-2", "section-3"],
                "difficulty": "débutant"
            },
            {
                "title": "Devenir un expert Lightning Network",
                "description": "Un parcours complet pour maîtriser le Lightning Network",
                "sections": ["section-4", "section-5", "section-6"],
                "difficulty": "intermédiaire"
            },
            {
                "title": "Architecture avancée du Lightning Network",
                "description": "Plongez dans les détails techniques du Lightning Network",
                "sections": ["section-7", "section-8", "section-9"],
                "difficulty": "avancé"
            }
        ]
        return learning_paths
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des parcours d'apprentissage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_content():
    """
    Rafraîchit le contenu du notebook depuis Notelm.
    
    Cette endpoint permet de forcer le rafraîchissement du contenu
    du notebook Lightning Network depuis l'API Notelm.
    
    Returns:
        Dict: Statut de l'opération et nombre de sections rafraîchies
    """
    try:
        content = await notelm_connector.fetch_notebook_content()
        sections = notelm_connector.parse_notebook_sections(content)
        
        # Dans une implémentation réelle, on sauvegarderait ces données dans une base de données
        # Pour l'instant, on retourne simplement le nombre de sections
        
        return {
            "status": "success",
            "message": "Contenu rafraîchi avec succès",
            "sections_count": len(sections)
        }
    except Exception as e:
        logger.error(f"Erreur lors du rafraîchissement du contenu: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 