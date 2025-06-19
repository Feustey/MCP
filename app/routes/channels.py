from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, List, Optional, Any
from app.services.lnbits import LNbitsService
from app.auth import verify_jwt_and_get_tenant

router = APIRouter(prefix="/channels", tags=["Channel Management"])

@router.get("/recommendations/amboss")
async def get_amboss_recommendations(
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère les recommandations de canaux depuis Amboss."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_amboss_channel_recommendations()

@router.get("/recommendations/unified")
async def get_unified_recommendations(
    authorization: str = Header(..., alias="Authorization")
):
    """Récupère les recommandations de canaux unifiées (toutes sources)."""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    lnbits_service = LNbitsService()
    return await lnbits_service.get_unified_channel_recommendations() 