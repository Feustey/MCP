# app/main.py
from fastapi import FastAPI
from app.routes import nodes, wallet, admin  # Importe aussi le routeur admin
from app.db import client, MONGO_DB, db # Importe le client et la db pour le shutdown
import uvicorn

app = FastAPI(
    title="DazNode Lightning API",
    description="API pour gérer les nodes Lightning Network et les opérations de portefeuille",
    version="0.1.0"
)

# Pas besoin d'événement startup si on utilise la dépendance Depends(get_database)
# La connexion est établie lors de l'initialisation du client Motor.
# @app.on_event("startup")
# async def startup_db_client():
#    # Optionnel : on pourrait mettre le client dans app.state si nécessaire ailleurs
#    # app.state.mongo_client = client
#    # app.state.db = db
#    print("Connexion à MongoDB établie...")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close() # Ferme la connexion Motor proprement à l'arrêt
    print("Connexion à MongoDB fermée.")

# Inclut les routes définies dans app/routes/nodes.py, wallet.py et admin.py
app.include_router(nodes.router)
app.include_router(wallet.router)
app.include_router(admin.router)

@app.get("/", tags=["Root"])
async def read_root():
    return {
        "message": "Bienvenue sur l'API DazNode Lightning",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

# Permet de lancer l'app avec `python app/main.py` pour le développement
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True # Recharge automatiquement lors des modifications du code
    ) 