#!/usr/bin/env python3
"""
API MCP Production - Point d'entrée principal pour Hostinger
Version complète avec tous les endpoints nécessaires
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import os
import psutil
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
app = FastAPI(
    title="MCP API Production",
    description="API MCP complète pour déploiement Hostinger",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === ENDPOINTS DE BASE ===

@app.get("/")
async def root():
    return JSONResponse(
        content={
            "service": "MCP Production API",
            "status": "operational",
            "version": "2.0.0",
            "platform": "hostinger",
            "timestamp": int(time.time()),
            "endpoints": {
                "health": "/health",
                "metrics": "/metrics", 
                "status": "/api/v1/status",
                "daznode": "/api/v1/daznode/status",
                "docs": "/docs"
            }
        }
    )

@app.get("/health")
async def health_check():
    """Check de santé complet"""
    try:
        # Métriques système de base
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return JSONResponse(
            content={
                "status": "healthy",
                "platform": "hostinger-production",
                "timestamp": int(time.time()),
                "uptime": int(time.time() - psutil.boot_time()),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": (disk.used / disk.total) * 100,
                    "load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": int(time.time())
            }
        )

@app.get("/metrics")
async def get_metrics():
    """Métriques système détaillées"""
    try:
        # Métriques système
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot_time = psutil.boot_time()
        
        # Processus
        process_count = len(psutil.pids())
        
        return {
            "timestamp": int(time.time()),
            "system": {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "processes": process_count,
                "uptime": int(time.time() - boot_time)
            },
            "api": {
                "version": "2.0.0",
                "requests_handled": "tracking_enabled",
                "status": "operational"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error collecting metrics: {str(e)}")

# === ENDPOINTS API V1 ===

@app.get("/api/v1/status")
async def api_status():
    """Statut global de l'API"""
    return {
        "service": "mcp-api",
        "version": "2.0.0",
        "platform": "hostinger-production",
        "status": "operational",
        "timestamp": int(time.time()),
        "environment": os.environ.get("ENVIRONMENT", "production"),
        "features": {
            "health_monitoring": True,
            "metrics_collection": True,
            "daznode_integration": True,
            "telegram_reports": True
        }
    }

@app.get("/api/v1/daznode/status")
async def daznode_status():
    """Statut du nœud Lightning Daznode"""
    # Simulation des données - à remplacer par de vraies données
    node_id = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
    
    return {
        "node_id": node_id,
        "alias": "DazNode ⚡🚀",
        "status": "online",
        "channels": {
            "active": 21,
            "total": 21,
            "capacity_sats": 36754901
        },
        "network": {
            "connected": True,
            "synced": True,
            "block_height": "current"
        },
        "last_update": int(time.time()),
        "monitoring": {
            "telegram_reports": True,
            "daily_schedule": "07:00 UTC",
            "next_report": "tomorrow 07:00"
        }
    }

@app.get("/api/v1/reports/health")
async def generate_health_report():
    """Génère un rapport de santé instantané"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Score de santé global
        health_score = 100
        if cpu_percent > 80:
            health_score -= 30
        elif cpu_percent > 60:
            health_score -= 15
            
        if memory.percent > 85:
            health_score -= 25
        elif memory.percent > 70:
            health_score -= 10
            
        if (disk.used / disk.total) * 100 > 90:
            health_score -= 20
            
        status = "excellent" if health_score >= 90 else "good" if health_score >= 70 else "warning" if health_score >= 50 else "critical"
        
        return {
            "timestamp": int(time.time()),
            "health_score": health_score,
            "status": status,
            "details": {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "status": "normal" if cpu_percent < 60 else "high" if cpu_percent < 80 else "critical"
                },
                "memory": {
                    "usage_percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "status": "normal" if memory.percent < 70 else "high" if memory.percent < 85 else "critical"
                },
                "disk": {
                    "usage_percent": round((disk.used / disk.total) * 100, 1),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "status": "normal" if (disk.used / disk.total) * 100 < 80 else "high" if (disk.used / disk.total) * 100 < 90 else "critical"
                }
            },
            "recommendations": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating health report: {str(e)}")

# === ENDPOINTS DE DEBUG ===

@app.get("/debug/info")
async def debug_info():
    """Informations de debug (production sécurisée)"""
    return {
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "platform": os.name,
        "cwd": os.getcwd(),
        "env_vars_count": len(os.environ),
        "timestamp": int(time.time()),
        "deployment_ready": True
    }

# === GESTION D'ERREURS ===

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "path": str(request.url.path),
            "available_endpoints": [
                "/", "/health", "/metrics", "/api/v1/status", 
                "/api/v1/daznode/status", "/api/v1/reports/health", "/docs"
            ]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": int(time.time()),
            "path": str(request.url.path)
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)