from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
from datetime import datetime

app = FastAPI(title="MCP API Simple")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def home():
    """Page d'accueil de l'API."""
    return """
    <html>
        <head>
            <title>MCP API Simple</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; color: #333; }
                h1 { color: #2c3e50; }
                .status { padding: 20px; background: #ecf0f1; border-radius: 5px; margin: 20px 0; }
                .endpoint { margin: 10px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #3498db; }
                .success { color: #27ae60; font-weight: bold; }
                ul { list-style-type: none; padding: 0; }
                li { margin: 8px 0; }
            </style>
        </head>
        <body>
            <h1>🚀 MCP API - Lightning Network Optimizer</h1>
            <div class="status">
                <p class="success">✅ API MCP opérationnelle et en cours d'exécution</p>
                <p><strong>Timestamp:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
            </div>
            
            <h2>📊 Services Disponibles</h2>
            <div class="endpoint">
                <h3>Endpoints API principaux :</h3>
                <ul>
                    <li><strong>GET /</strong> - Page d'accueil (cette page)</li>
                    <li><strong>GET /health</strong> - Vérification de l'état de l'API</li>
                    <li><strong>GET /status</strong> - État détaillé du système</li>
                    <li><strong>GET /docs</strong> - Documentation interactive Swagger</li>
                    <li><strong>GET /redoc</strong> - Documentation ReDoc</li>
                </ul>
            </div>
            
            <h2>🔧 Services Infrastructure Locaux</h2>
            <div class="endpoint">
                <ul>
                    <li><strong>MongoDB:</strong> <a href="http://localhost:27017" target="_blank">localhost:27017</a></li>
                    <li><strong>Redis:</strong> localhost:6379</li>
                    <li><strong>LNBits Test:</strong> <a href="http://localhost:5001" target="_blank">localhost:5001</a></li>
                    <li><strong>Prometheus:</strong> <a href="http://localhost:9090" target="_blank">localhost:9090</a></li>
                    <li><strong>Metrics:</strong> <a href="http://localhost:9091/metrics" target="_blank">localhost:9091/metrics</a></li>
                </ul>
            </div>
            
            <h2>⚡ Fonctionnalités</h2>
            <div class="endpoint">
                <p>Cette API fait partie du système MCP (Monitoring, Control, and Planning) pour l'optimisation des nœuds Lightning Network.</p>
                <p><strong>Note:</strong> Système en cours de développement. Certaines fonctionnalités avancées sont en cours d'implémentation.</p>
            </div>
                 </body>
     </html>
     """

@app.get("/health")
async def health_check():
    """Endpoint de vérification de l'état de l'API."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0-simple",
        "services": {
            "api": "running",
            "mongodb": "available on localhost:27017",
            "redis": "available on localhost:6379",
            "lnbits_test": "available on localhost:5001",
            "prometheus": "available on localhost:9090"
        }
    }

@app.get("/status")
async def system_status():
    """État détaillé du système."""
    return {
        "system": "MCP Lightning Network Optimizer",
        "api_status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "development",
        "available_endpoints": [
            {"path": "/", "method": "GET", "description": "Page d'accueil"},
            {"path": "/health", "method": "GET", "description": "Vérification santé"},
            {"path": "/status", "method": "GET", "description": "État système"},
            {"path": "/docs", "method": "GET", "description": "Documentation Swagger"},
            {"path": "/redoc", "method": "GET", "description": "Documentation ReDoc"}
        ],
        "local_services": {
            "mongodb": {"url": "localhost:27017", "status": "should_be_running"},
            "redis": {"url": "localhost:6379", "status": "should_be_running"},
            "lnbits_test": {"url": "localhost:5001", "status": "should_be_running"},
            "prometheus": {"url": "localhost:9090", "status": "should_be_running"},
            "metrics_exporter": {"url": "localhost:9091", "status": "should_be_running"}
        }
    }

if __name__ == "__main__":
    print("🚀 Lancement de l'API MCP Simple...")
    print("📍 Disponible sur: http://localhost:8000")
    print("📖 Documentation: http://localhost:8000/docs")
    print("🔍 Santé: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info") 