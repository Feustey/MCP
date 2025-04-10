from fastapi import APIRouter, HTTPException, Request
from datetime import datetime

router = APIRouter(prefix="/sparkseer", tags=["SparkSeer"])

@router.get("/health")
async def sparkseer_health():
    """Endpoint de vérification de l'état du service SparkSeer."""
    return {
        "service": "SparkSeer",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat()
    }
