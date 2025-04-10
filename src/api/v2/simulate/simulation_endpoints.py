from fastapi import APIRouter, HTTPException, Depends, Query, Body, BackgroundTasks, WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import asyncio
import json
import uuid
import numpy as np
from src.auth.jwt import get_current_user
from src.auth.models import User

# Créer le router
router = APIRouter(
    prefix="/simulate",
    tags=["Simulation v2"],
    responses={
        401: {"description": "Non authentifié"},
        403: {"description": "Accès refusé"},
        429: {"description": "Trop de requêtes"},
        500: {"description": "Erreur serveur"}
    }
)

# Gestionnaire des simulations
class SimulationManager:
    """Gestionnaire pour les simulations en cours"""
    
    def __init__(self):
        """Initialise le gestionnaire de simulation"""
        self.simulations = {}  # simulation_id -> simulation_data
        self.results = {}      # simulation_id -> results
        self.callbacks = {}    # simulation_id -> list of callback functions
        self.websockets = {}   # simulation_id -> list of websockets
    
    def register_simulation(self, simulation_data: Dict) -> str:
        """
        Enregistre une nouvelle simulation
        
        Args:
            simulation_data: Données de configuration de la simulation
            
        Returns:
            ID unique de la simulation
        """
        simulation_id = str(uuid.uuid4())
        self.simulations[simulation_id] = simulation_data
        self.results[simulation_id] = {
            "status": "pending",
            "progress": 0,
            "created_at": datetime.utcnow(),
            "data": None
        }
        self.callbacks[simulation_id] = []
        self.websockets[simulation_id] = []
        return simulation_id
    
    def get_simulation(self, simulation_id: str) -> Optional[Dict]:
        """
        Récupère les données d'une simulation
        
        Args:
            simulation_id: ID de la simulation
            
        Returns:
            Données de la simulation ou None si elle n'existe pas
        """
        return self.simulations.get(simulation_id)
    
    def get_results(self, simulation_id: str) -> Optional[Dict]:
        """
        Récupère les résultats d'une simulation
        
        Args:
            simulation_id: ID de la simulation
            
        Returns:
            Résultats de la simulation ou None si elle n'existe pas
        """
        return self.results.get(simulation_id)
    
    def update_progress(self, simulation_id: str, progress: float):
        """
        Met à jour la progression d'une simulation
        
        Args:
            simulation_id: ID de la simulation
            progress: Progression (0-100)
        """
        if simulation_id in self.results:
            self.results[simulation_id]["progress"] = progress
            self._notify_progress(simulation_id)
    
    def set_result(self, simulation_id: str, data: Any):
        """
        Définit le résultat d'une simulation
        
        Args:
            simulation_id: ID de la simulation
            data: Données résultantes
        """
        if simulation_id in self.results:
            self.results[simulation_id]["status"] = "completed"
            self.results[simulation_id]["progress"] = 100
            self.results[simulation_id]["completed_at"] = datetime.utcnow()
            self.results[simulation_id]["data"] = data
            self._notify_completion(simulation_id)
    
    def set_error(self, simulation_id: str, error: str):
        """
        Définit une erreur pour une simulation
        
        Args:
            simulation_id: ID de la simulation
            error: Message d'erreur
        """
        if simulation_id in self.results:
            self.results[simulation_id]["status"] = "error"
            self.results[simulation_id]["error"] = error
            self.results[simulation_id]["completed_at"] = datetime.utcnow()
            self._notify_error(simulation_id)
    
    def register_callback(self, simulation_id: str, callback):
        """
        Enregistre une fonction de rappel pour les mises à jour
        
        Args:
            simulation_id: ID de la simulation
            callback: Fonction à appeler lors des mises à jour
        """
        if simulation_id in self.callbacks:
            self.callbacks[simulation_id].append(callback)
    
    def register_websocket(self, simulation_id: str, websocket: WebSocket):
        """
        Enregistre un websocket pour les mises à jour en temps réel
        
        Args:
            simulation_id: ID de la simulation
            websocket: WebSocket connecté
        """
        if simulation_id in self.websockets:
            self.websockets[simulation_id].append(websocket)
    
    def remove_websocket(self, simulation_id: str, websocket: WebSocket):
        """
        Retire un websocket des notifications
        
        Args:
            simulation_id: ID de la simulation
            websocket: WebSocket à retirer
        """
        if simulation_id in self.websockets and websocket in self.websockets[simulation_id]:
            self.websockets[simulation_id].remove(websocket)
    
    async def _notify_progress(self, simulation_id: str):
        """Notifie les observateurs de la progression"""
        if simulation_id in self.results:
            data = {
                "type": "progress",
                "simulation_id": simulation_id,
                "progress": self.results[simulation_id]["progress"]
            }
            await self._send_notifications(simulation_id, data)
    
    async def _notify_completion(self, simulation_id: str):
        """Notifie les observateurs de la complétion"""
        if simulation_id in self.results:
            data = {
                "type": "completed",
                "simulation_id": simulation_id,
                "result": "success"
            }
            await self._send_notifications(simulation_id, data)
    
    async def _notify_error(self, simulation_id: str):
        """Notifie les observateurs d'une erreur"""
        if simulation_id in self.results:
            data = {
                "type": "error",
                "simulation_id": simulation_id,
                "error": self.results[simulation_id].get("error", "Unknown error")
            }
            await self._send_notifications(simulation_id, data)
    
    async def _send_notifications(self, simulation_id: str, data: Dict):
        """Envoie les notifications à tous les observateurs"""
        # Appeler les callbacks
        for callback in self.callbacks.get(simulation_id, []):
            try:
                callback(data)
            except Exception as e:
                print(f"Error in callback: {e}")
        
        # Envoyer aux websockets
        for ws in self.websockets.get(simulation_id, []):
            try:
                await ws.send_json(data)
            except Exception as e:
                print(f"Error sending to websocket: {e}")

# Initialisation du gestionnaire
simulation_manager = SimulationManager()

# Modèles de données pour les requêtes et réponses
class NetworkGrowthParams(BaseModel):
    """Paramètres pour la simulation de croissance du réseau"""
    initial_nodes: int = Field(10000, description="Nombre initial de nœuds", ge=1000, le=100000)
    growth_rate: float = Field(0.05, description="Taux de croissance mensuel", ge=0, le=1)
    simulation_months: int = Field(12, description="Nombre de mois à simuler", ge=1, le=60)
    add_random_variation: bool = Field(True, description="Ajouter des variations aléatoires")
    model_external_factors: bool = Field(True, description="Modéliser des facteurs externes (nouvelles, adoption, etc.)")

class FeeMarketParams(BaseModel):
    """Paramètres pour la simulation du marché des frais"""
    initial_avg_fee_rate: int = Field(500, description="Taux de frais moyen initial (ppm)", ge=1, le=10000)
    competitive_pressure: float = Field(0.1, description="Pression de la concurrence (0-1)", ge=0, le=1)
    demand_growth: float = Field(0.03, description="Croissance mensuelle de la demande", ge=0, le=1)
    include_price_elasticity: bool = Field(True, description="Inclure l'élasticité des prix")
    simulation_months: int = Field(12, description="Nombre de mois à simuler", ge=1, le=60)

class AttackScenarioParams(BaseModel):
    """Paramètres pour la simulation de scénarios d'attaque"""
    attack_type: str = Field("routing_table_manipulation", description="Type d'attaque")
    network_size: int = Field(10000, description="Taille du réseau (nombre de nœuds)", ge=1000, le=100000)
    attacker_resources: float = Field(0.05, description="Ressources de l'attaquant (% du réseau)", ge=0.001, le=0.5)
    defense_level: float = Field(0.5, description="Niveau de défense du réseau (0-1)", ge=0, le=1)
    simulation_days: int = Field(30, description="Nombre de jours à simuler", ge=1, le=365)

class SimulationResponse(BaseModel):
    """Réponse initiale pour une simulation en cours"""
    simulation_id: str = Field(..., description="Identifiant unique de la simulation")
    status: str = Field(..., description="État de la simulation")
    estimated_duration: int = Field(..., description="Durée estimée en secondes")
    created_at: datetime = Field(..., description="Date de création de la simulation")
    polling_url: str = Field(..., description="URL pour interroger l'état de la simulation")
    websocket_url: str = Field(..., description="URL pour suivre la simulation en temps réel")

class SimulationStatus(BaseModel):
    """État d'une simulation"""
    simulation_id: str = Field(..., description="Identifiant unique de la simulation")
    status: str = Field(..., description="État de la simulation (pending, running, completed, error)")
    progress: float = Field(..., description="Progression de la simulation (0-100)")
    created_at: datetime = Field(..., description="Date de création de la simulation")
    completed_at: Optional[datetime] = Field(None, description="Date de complétion de la simulation")
    error: Optional[str] = Field(None, description="Message d'erreur en cas d'échec")

# Fonctions de simulation
async def run_network_growth_simulation(simulation_id: str, params: NetworkGrowthParams):
    """
    Exécute une simulation de croissance du réseau
    
    Args:
        simulation_id: ID de la simulation
        params: Paramètres de la simulation
    """
    try:
        # Simuler un traitement en arrière-plan
        total_steps = params.simulation_months
        
        # Initialiser les données
        nodes = params.initial_nodes
        channels = nodes * 5  # Hypothèse : 5 canaux par nœud en moyenne
        capacity = nodes * 1000000  # Hypothèse : 1M sats par nœud en moyenne
        
        # Préparer les résultats
        time_points = []
        node_counts = []
        channel_counts = []
        capacity_values = []
        
        for step in range(total_steps + 1):
            # Mettre à jour la progression
            progress = (step / total_steps) * 100
            simulation_manager.update_progress(simulation_id, progress)
            
            # Calculer le temps simulé
            current_time = datetime.utcnow() + timedelta(days=step * 30)
            
            # Ajouter des variations si demandé
            variation = 1.0
            if params.add_random_variation:
                variation = np.random.normal(1.0, 0.05)  # 5% de variation
            
            # Modéliser des facteurs externes
            external_factor = 1.0
            if params.model_external_factors:
                # Simuler un événement majeur tous les 3 mois
                if step > 0 and step % 3 == 0:
                    external_factor = np.random.uniform(0.9, 1.3)  # Entre -10% et +30%
            
            # Calculer la croissance pour ce mois
            if step > 0:
                monthly_growth = (1 + params.growth_rate) * variation * external_factor
                nodes = int(nodes * monthly_growth)
                channels = int(channels * monthly_growth * 1.1)  # Les canaux croissent plus vite
                capacity = capacity * monthly_growth * 1.15  # La capacité croît encore plus vite
            
            # Enregistrer les données
            time_points.append(current_time.isoformat())
            node_counts.append(nodes)
            channel_counts.append(channels)
            capacity_values.append(capacity)
            
            # Attendre un peu pour simuler un calcul intensif
            await asyncio.sleep(0.2)
        
        # Préparer le résultat final
        result = {
            "time_points": time_points,
            "metrics": {
                "nodes": node_counts,
                "channels": channel_counts,
                "capacity": capacity_values
            },
            "parameters": params.dict(),
            "insights": [
                "Le réseau a connu une croissance de {}% sur la période simulée".format(
                    round((node_counts[-1] / node_counts[0] - 1) * 100, 2)
                ),
                "Le nombre moyen de canaux par nœud est passé de {:.2f} à {:.2f}".format(
                    channel_counts[0] / node_counts[0],
                    channel_counts[-1] / node_counts[-1]
                ),
                "La capacité moyenne par nœud est passée de {:.2f} à {:.2f} sats".format(
                    capacity_values[0] / node_counts[0],
                    capacity_values[-1] / node_counts[-1]
                )
            ]
        }
        
        # Enregistrer le résultat
        simulation_manager.set_result(simulation_id, result)
    
    except Exception as e:
        simulation_manager.set_error(simulation_id, str(e))

async def run_fee_market_simulation(simulation_id: str, params: FeeMarketParams):
    """
    Exécute une simulation du marché des frais
    
    Args:
        simulation_id: ID de la simulation
        params: Paramètres de la simulation
    """
    try:
        # Simuler un traitement en arrière-plan
        total_steps = params.simulation_months
        
        # Initialiser les données
        fee_rate = params.initial_avg_fee_rate
        transaction_volume = 1000000  # Volume initial (en satoshis)
        
        # Préparer les résultats
        time_points = []
        fee_rates = []
        volumes = []
        revenues = []
        
        for step in range(total_steps + 1):
            # Mettre à jour la progression
            progress = (step / total_steps) * 100
            simulation_manager.update_progress(simulation_id, progress)
            
            # Calculer le temps simulé
            current_time = datetime.utcnow() + timedelta(days=step * 30)
            
            # Calculer l'évolution pour ce mois
            if step > 0:
                # Effet de la concurrence sur les frais
                fee_pressure = params.competitive_pressure * np.random.uniform(0.8, 1.2)
                fee_rate = max(1, int(fee_rate * (1 - fee_pressure * 0.05)))
                
                # Croissance du volume
                volume_growth = params.demand_growth * np.random.uniform(0.9, 1.1)
                
                # Élasticité des prix si activée
                if params.include_price_elasticity:
                    # Plus les frais baissent, plus le volume augmente
                    elasticity_factor = 1 + (0.02 * (1 - fee_rate / params.initial_avg_fee_rate))
                    volume_growth *= elasticity_factor
                
                transaction_volume *= (1 + volume_growth)
            
            # Calculer les revenus
            revenue = transaction_volume * fee_rate / 1000000  # ppm -> proportion
            
            # Enregistrer les données
            time_points.append(current_time.isoformat())
            fee_rates.append(fee_rate)
            volumes.append(transaction_volume)
            revenues.append(revenue)
            
            # Attendre un peu pour simuler un calcul intensif
            await asyncio.sleep(0.2)
        
        # Préparer le résultat final
        result = {
            "time_points": time_points,
            "metrics": {
                "fee_rates": fee_rates,
                "transaction_volumes": volumes,
                "revenues": revenues
            },
            "parameters": params.dict(),
            "insights": [
                "Le taux de frais moyen a évolué de {} à {} ppm".format(
                    fee_rates[0], fee_rates[-1]
                ),
                "Le volume de transactions a augmenté de {}%".format(
                    round((volumes[-1] / volumes[0] - 1) * 100, 2)
                ),
                "Les revenus totaux ont évolué de {}%".format(
                    round((revenues[-1] / revenues[0] - 1) * 100, 2)
                ),
                "Point d'équilibre optimal estimé : {} ppm".format(
                    round(fee_rates[revenues.index(max(revenues))], 2)
                )
            ]
        }
        
        # Enregistrer le résultat
        simulation_manager.set_result(simulation_id, result)
    
    except Exception as e:
        simulation_manager.set_error(simulation_id, str(e))

async def run_attack_scenario_simulation(simulation_id: str, params: AttackScenarioParams):
    """
    Exécute une simulation de scénario d'attaque
    
    Args:
        simulation_id: ID de la simulation
        params: Paramètres de la simulation
    """
    try:
        # Simuler un traitement en arrière-plan
        total_steps = params.simulation_days
        
        # Initialiser les données selon le type d'attaque
        if params.attack_type == "routing_table_manipulation":
            attack_success_rate = 0.3 * (1 - params.defense_level)
            attack_impact = 0.2 * params.attacker_resources
        elif params.attack_type == "channel_jamming":
            attack_success_rate = 0.5 * (1 - params.defense_level)
            attack_impact = 0.3 * params.attacker_resources
        elif params.attack_type == "eclipse_attack":
            attack_success_rate = 0.2 * (1 - params.defense_level)
            attack_impact = 0.4 * params.attacker_resources
        else:
            attack_success_rate = 0.4 * (1 - params.defense_level)
            attack_impact = 0.25 * params.attacker_resources
        
        # Initialiser les metrics
        network_health = 1.0  # 1.0 = 100% sain
        successful_payments = 1.0  # Taux de paiements réussis
        
        # Préparer les résultats
        time_points = []
        health_values = []
        payment_success_rates = []
        attack_progression = []
        defense_effectiveness = []
        
        for step in range(total_steps + 1):
            # Mettre à jour la progression
            progress = (step / total_steps) * 100
            simulation_manager.update_progress(simulation_id, progress)
            
            # Calculer le temps simulé
            current_time = datetime.utcnow() + timedelta(days=step)
            
            # Simuler l'évolution de l'attaque et des défenses
            if step > 0:
                # L'attaque progresse
                attack_progression_value = min(1.0, (step / total_steps) * 1.5)
                
                # Les défenses s'améliorent (plus lentement)
                defense_improvement = min(0.5, (step / total_steps) * 0.2)
                current_defense = params.defense_level + (defense_improvement * (1 - params.defense_level))
                
                # Impact de l'attaque sur le réseau
                daily_impact = attack_impact * attack_progression_value * attack_success_rate * (1 - current_defense)
                network_health = max(0.3, network_health - daily_impact * 0.05)
                
                # Impact sur les paiements
                successful_payments = max(0.2, network_health * 0.7 + 0.3)  # Au minimum 20% réussissent
            
            # Enregistrer les données
            time_points.append(current_time.isoformat())
            health_values.append(network_health)
            payment_success_rates.append(successful_payments)
            attack_progression.append(attack_progression_value if step > 0 else 0)
            defense_effectiveness.append(current_defense if step > 0 else params.defense_level)
            
            # Attendre un peu pour simuler un calcul intensif
            await asyncio.sleep(0.1)
        
        # Préparer le résultat final
        result = {
            "time_points": time_points,
            "metrics": {
                "network_health": health_values,
                "payment_success_rates": payment_success_rates,
                "attack_progression": attack_progression,
                "defense_effectiveness": defense_effectiveness
            },
            "parameters": params.dict(),
            "insights": [
                "Impact maximal de l'attaque : {}% de dégradation du réseau".format(
                    round((1 - min(health_values)) * 100, 2)
                ),
                "Taux minimal de paiements réussis : {}%".format(
                    round(min(payment_success_rates) * 100, 2)
                ),
                "L'amélioration des défenses a réduit l'impact de {}%".format(
                    round((defense_effectiveness[-1] - defense_effectiveness[0]) * 100, 2)
                ),
                "Temps de récupération estimé après l'attaque : {} jours".format(
                    round(params.simulation_days * 0.5)
                )
            ]
        }
        
        # Enregistrer le résultat
        simulation_manager.set_result(simulation_id, result)
    
    except Exception as e:
        simulation_manager.set_error(simulation_id, str(e))

# Routes API
@router.post("/network-growth", response_model=SimulationResponse)
async def simulate_network_growth(
    params: NetworkGrowthParams = Body(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user)
):
    """
    Simule la croissance du réseau Lightning.
    
    Cette endpoint lance une simulation pour prévoir l'évolution du réseau Lightning
    en termes de nombre de nœuds, canaux et capacité totale.
    
    La simulation tient compte du taux de croissance spécifié et peut inclure
    des facteurs externes comme les nouvelles du marché ou l'adoption globale.
    """
    try:
        # Estimer la durée en fonction des paramètres
        estimated_duration = params.simulation_months * 0.5  # 0.5 seconde par mois simulé
        
        # Enregistrer la simulation
        simulation_id = simulation_manager.register_simulation(params.dict())
        
        # Lancer la simulation en arrière-plan
        asyncio.create_task(run_network_growth_simulation(simulation_id, params))
        
        # Construire l'URL de polling et de websocket
        polling_url = f"/api/v2/simulate/status/{simulation_id}"
        websocket_url = f"/api/v2/simulate/ws/{simulation_id}"
        
        # Créer la réponse
        response = SimulationResponse(
            simulation_id=simulation_id,
            status="pending",
            estimated_duration=int(estimated_duration),
            created_at=datetime.utcnow(),
            polling_url=polling_url,
            websocket_url=websocket_url
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du lancement de la simulation: {str(e)}")

@router.post("/fee-market", response_model=SimulationResponse)
async def simulate_fee_market(
    params: FeeMarketParams = Body(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user)
):
    """
    Simule l'évolution du marché des frais Lightning.
    
    Cette endpoint lance une simulation pour prévoir l'évolution des frais
    sur le réseau Lightning en fonction de la pression concurrentielle,
    de la croissance de la demande et d'autres facteurs.
    
    La simulation peut inclure l'élasticité des prix pour modéliser comment
    les changements de frais affectent le volume des transactions.
    """
    try:
        # Estimer la durée en fonction des paramètres
        estimated_duration = params.simulation_months * 0.5  # 0.5 seconde par mois simulé
        
        # Enregistrer la simulation
        simulation_id = simulation_manager.register_simulation(params.dict())
        
        # Lancer la simulation en arrière-plan
        asyncio.create_task(run_fee_market_simulation(simulation_id, params))
        
        # Construire l'URL de polling et de websocket
        polling_url = f"/api/v2/simulate/status/{simulation_id}"
        websocket_url = f"/api/v2/simulate/ws/{simulation_id}"
        
        # Créer la réponse
        response = SimulationResponse(
            simulation_id=simulation_id,
            status="pending",
            estimated_duration=int(estimated_duration),
            created_at=datetime.utcnow(),
            polling_url=polling_url,
            websocket_url=websocket_url
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du lancement de la simulation: {str(e)}")

@router.post("/attack-scenarios", response_model=SimulationResponse)
async def simulate_attack_scenarios(
    params: AttackScenarioParams = Body(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user)
):
    """
    Simule différents scénarios d'attaque sur le réseau Lightning.
    
    Cette endpoint lance une simulation pour modéliser les effets de
    différents types d'attaques sur le réseau Lightning, avec différents
    niveaux de ressources pour l'attaquant et de défenses pour le réseau.
    
    Les types d'attaques supportés incluent:
    - routing_table_manipulation: Manipulation des tables de routage
    - channel_jamming: Saturation de canaux
    - eclipse_attack: Attaques d'éclipse
    """
    try:
        # Estimer la durée en fonction des paramètres
        estimated_duration = params.simulation_days * 0.25  # 0.25 seconde par jour simulé
        
        # Enregistrer la simulation
        simulation_id = simulation_manager.register_simulation(params.dict())
        
        # Lancer la simulation en arrière-plan
        asyncio.create_task(run_attack_scenario_simulation(simulation_id, params))
        
        # Construire l'URL de polling et de websocket
        polling_url = f"/api/v2/simulate/status/{simulation_id}"
        websocket_url = f"/api/v2/simulate/ws/{simulation_id}"
        
        # Créer la réponse
        response = SimulationResponse(
            simulation_id=simulation_id,
            status="pending",
            estimated_duration=int(estimated_duration),
            created_at=datetime.utcnow(),
            polling_url=polling_url,
            websocket_url=websocket_url
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du lancement de la simulation: {str(e)}")

@router.get("/status/{simulation_id}", response_model=SimulationStatus)
async def get_simulation_status(
    simulation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupère l'état d'une simulation en cours ou terminée.
    
    Cette endpoint permet de suivre l'état d'une simulation précédemment lancée,
    y compris sa progression, son statut et ses éventuelles erreurs.
    """
    results = simulation_manager.get_results(simulation_id)
    if not results:
        raise HTTPException(status_code=404, detail="Simulation non trouvée")
    
    return SimulationStatus(
        simulation_id=simulation_id,
        status=results["status"],
        progress=results["progress"],
        created_at=results["created_at"],
        completed_at=results.get("completed_at"),
        error=results.get("error")
    )

@router.get("/results/{simulation_id}")
async def get_simulation_results(
    simulation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les résultats d'une simulation terminée.
    
    Cette endpoint retourne les résultats complets d'une simulation qui a
    été exécutée avec succès, y compris toutes les métriques simulées et
    les insights générés par l'analyse.
    """
    results = simulation_manager.get_results(simulation_id)
    if not results:
        raise HTTPException(status_code=404, detail="Simulation non trouvée")
    
    if results["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"La simulation n'est pas terminée (état: {results['status']})")
    
    return results["data"]

@router.websocket("/ws/{simulation_id}")
async def websocket_endpoint(websocket: WebSocket, simulation_id: str):
    """
    Établit une connexion WebSocket pour recevoir des mises à jour en temps réel
    sur une simulation en cours.
    
    Cette endpoint permet de suivre en temps réel la progression d'une simulation,
    sans avoir à interroger régulièrement l'API REST.
    """
    await websocket.accept()
    
    # Vérifier que la simulation existe
    if not simulation_manager.get_simulation(simulation_id):
        await websocket.send_json({
            "type": "error",
            "message": "Simulation non trouvée"
        })
        await websocket.close()
        return
    
    # Enregistrer le websocket
    simulation_manager.register_websocket(simulation_id, websocket)
    
    try:
        # Envoyer l'état initial
        results = simulation_manager.get_results(simulation_id)
        await websocket.send_json({
            "type": "status",
            "simulation_id": simulation_id,
            "status": results["status"],
            "progress": results["progress"]
        })
        
        # Attendre que la connexion soit fermée
        while True:
            data = await websocket.receive_text()
            # On pourrait traiter des commandes ici si nécessaire
            await asyncio.sleep(1)
    
    except WebSocketDisconnect:
        # Nettoyer lorsque le client se déconnecte
        simulation_manager.remove_websocket(simulation_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        # Nettoyer en cas d'erreur
        simulation_manager.remove_websocket(simulation_id, websocket) 