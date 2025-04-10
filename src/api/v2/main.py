from fastapi import APIRouter
from .network_graph.routes import router as network_graph_router
from .predict.prediction_endpoints import router as predict_router
from .simulate.simulation_endpoints import router as simulate_router
from .monitor.monitor_endpoints import router as monitor_router

# Créer le routeur principal pour l'API v2
api_v2_router = APIRouter(prefix="/api/v2")

# Inclure les routeurs spécifiques
api_v2_router.include_router(network_graph_router)
api_v2_router.include_router(predict_router)
api_v2_router.include_router(simulate_router)
api_v2_router.include_router(monitor_router)

# Ajouter d'autres routeurs au fur et à mesure de leur création
# api_v2_router.include_router(autre_router) 