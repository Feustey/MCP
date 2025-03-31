from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
from lightning import router as lightning_router
from server import router as sparkseer_router

app = FastAPI(title="MCP API")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routes
app.include_router(lightning_router)
app.include_router(sparkseer_router)

@app.get("/", response_class=HTMLResponse)
async def home():
    """Page d'accueil de l'API."""
    return """
    <html>
        <head>
            <title>MCP API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                .endpoint { margin: 20px 0; padding: 10px; background: #f5f5f5; }
            </style>
        </head>
        <body>
            <h1>Bienvenue sur l'API MCP</h1>
            <p>Cette API permet d'analyser et d'optimiser votre présence sur le réseau Lightning.</p>
            <div class="endpoint">
                <h2>Endpoints disponibles :</h2>
                <ul>
                    <li><strong>GET /health</strong> - Vérification de l'état de l'API</li>
                    <li><strong>POST /lightning/validate-key</strong> - Validation de clé Lightning</li>
                    <li><strong>POST /lightning/validate-node</strong> - Validation de node Lightning</li>
                    <li><strong>POST /optimize-node</strong> - Optimisation de nœud</li>
                    <li><strong>GET /node/{node_id}/stats</strong> - Statistiques du nœud</li>
                    <li><strong>GET /node/{node_id}/history</strong> - Historique du nœud</li>
                    <li><strong>GET /network-summary</strong> - Résumé du réseau</li>
                    <li><strong>GET /centralities</strong> - Centralités des nœuds</li>
                    <li><strong>POST /node/{node_id}/optimize</strong> - Optimisation complète du nœud</li>
                </ul>
            </div>
        </body>
    </html>
    """

@app.get("/health")
async def health_check(request: Request):
    """Endpoint de vérification de l'état de l'API."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 