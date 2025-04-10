from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging
import asyncio
from .models import (
    SimulationScenario, SimulationRequest, SimulationResult,
    SimulationFilter, SimulationType, SimulationStatus
)

# Configuration du logging
logger = logging.getLogger(__name__)

# Création du router
router = APIRouter(
    prefix="/simulate",
    tags=["simulation"],
    responses={
        401: {"description": "Non autorisé"},
        403: {"description": "Accès interdit"},
        404: {"description": "Ressource non trouvée"},
        500: {"description": "Erreur interne du serveur"}
    }
)

# Base de données temporaire en mémoire (à remplacer par une vraie base de données)
class SimulationDB:
    def __init__(self):
        self.scenarios: Dict[str, SimulationScenario] = {}
        self.simulations: Dict[str, SimulationResult] = {}

# Instance de la base de données
db = SimulationDB()

# Routes pour la gestion des scénarios
@router.post("/scenarios", response_model=SimulationScenario, status_code=status.HTTP_201_CREATED)
async def create_scenario(scenario: SimulationScenario):
    """Créer un nouveau scénario de simulation"""
    scenario_id = f"scenario-{uuid.uuid4().hex[:8]}"
    new_scenario = SimulationScenario(
        id=scenario_id,
        **scenario.dict(exclude={'id'}),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.scenarios[scenario_id] = new_scenario
    return new_scenario

@router.get("/scenarios", response_model=List[SimulationScenario])
async def list_scenarios(
    type: Optional[SimulationType] = None
):
    """Lister les scénarios de simulation avec filtrage"""
    scenarios = list(db.scenarios.values())
    
    if type:
        scenarios = [s for s in scenarios if s.type == type]
    
    return scenarios

@router.get("/scenarios/{scenario_id}", response_model=SimulationScenario)
async def get_scenario(scenario_id: str = Path(..., description="ID du scénario")):
    """Obtenir les détails d'un scénario"""
    if scenario_id not in db.scenarios:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")
    return db.scenarios[scenario_id]

@router.put("/scenarios/{scenario_id}", response_model=SimulationScenario)
async def update_scenario(
    scenario_id: str = Path(..., description="ID du scénario"),
    scenario_update: SimulationScenario = None
):
    """Mettre à jour un scénario"""
    if scenario_id not in db.scenarios:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")
    
    scenario = db.scenarios[scenario_id]
    update_data = scenario_update.dict(exclude={'id', 'created_at'})
    for field, value in update_data.items():
        setattr(scenario, field, value)
    scenario.updated_at = datetime.utcnow()
    
    return scenario

@router.delete("/scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(scenario_id: str = Path(..., description="ID du scénario")):
    """Supprimer un scénario"""
    if scenario_id not in db.scenarios:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")
    del db.scenarios[scenario_id]

# Routes pour les simulations
@router.post("/run", response_model=SimulationResult)
async def run_simulation(request: SimulationRequest):
    """Lancer une simulation"""
    if request.scenario_id not in db.scenarios:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")
    
    scenario = db.scenarios[request.scenario_id]
    simulation_id = f"sim-{uuid.uuid4().hex[:8]}"
    
    # Créer le résultat initial
    result = SimulationResult(
        id=simulation_id,
        scenario_id=request.scenario_id,
        status=SimulationStatus.PENDING,
        start_time=datetime.utcnow(),
        results={},
        metrics={},
        events=[]
    )
    db.simulations[simulation_id] = result
    
    # Lancer la simulation de manière asynchrone
    asyncio.create_task(execute_simulation(result, request))
    
    return result

@router.get("/simulations", response_model=List[SimulationResult])
async def list_simulations(
    filter: SimulationFilter = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Lister les simulations avec filtrage"""
    simulations = list(db.simulations.values())
    
    if filter.scenario_id:
        simulations = [s for s in simulations if s.scenario_id == filter.scenario_id]
    if filter.type:
        simulations = [s for s in simulations if db.scenarios[s.scenario_id].type == filter.type]
    if filter.status:
        simulations = [s for s in simulations if s.status == filter.status]
    if filter.start_time:
        simulations = [s for s in simulations if s.start_time >= filter.start_time]
    if filter.end_time:
        simulations = [s for s in simulations if s.end_time <= filter.end_time]
    
    return simulations[skip:skip + limit]

@router.get("/simulations/{simulation_id}", response_model=SimulationResult)
async def get_simulation(simulation_id: str = Path(..., description="ID de la simulation")):
    """Obtenir les détails d'une simulation"""
    if simulation_id not in db.simulations:
        raise HTTPException(status_code=404, detail="Simulation non trouvée")
    return db.simulations[simulation_id]

@router.post("/simulations/{simulation_id}/cancel", response_model=SimulationResult)
async def cancel_simulation(simulation_id: str = Path(..., description="ID de la simulation")):
    """Annuler une simulation en cours"""
    if simulation_id not in db.simulations:
        raise HTTPException(status_code=404, detail="Simulation non trouvée")
    
    simulation = db.simulations[simulation_id]
    if simulation.status != SimulationStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Seules les simulations en cours peuvent être annulées")
    
    simulation.status = SimulationStatus.CANCELLED
    simulation.end_time = datetime.utcnow()
    
    return simulation

# Fonctions utilitaires
async def execute_simulation(result: SimulationResult, request: SimulationRequest):
    """Exécuter une simulation"""
    try:
        # Mettre à jour le statut
        result.status = SimulationStatus.RUNNING
        db.simulations[result.id] = result
        
        # Simuler l'exécution
        await simulate_execution(result, request)
        
        # Mettre à jour le statut en cas de succès
        result.status = SimulationStatus.COMPLETED
        result.end_time = datetime.utcnow()
        db.simulations[result.id] = result
        
    except Exception as e:
        # Gérer les erreurs
        result.status = SimulationStatus.FAILED
        result.error_message = str(e)
        result.end_time = datetime.utcnow()
        db.simulations[result.id] = result
        logger.error(f"Erreur lors de l'exécution de la simulation {result.id}: {e}")

async def simulate_execution(result: SimulationResult, request: SimulationRequest):
    """Simuler l'exécution d'une simulation"""
    # Simuler un délai d'exécution
    await asyncio.sleep(request.duration)
    
    # Générer des résultats simulés
    result.results = {
        "successful_payments": 485,
        "failed_payments": 15,
        "average_route_length": 3.2
    }
    
    result.metrics = {
        "success_rate": 0.97,
        "average_fee": 100,
        "max_route_length": 5
    }
    
    result.events = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "payment_success",
            "details": {"payment_id": f"pay-{uuid.uuid4().hex[:8]}", "amount": 50000}
        }
    ]
    
    result.metadata = {
        "simulation_duration": f"{request.duration}s",
        "cpu_usage": "45%"
    } 