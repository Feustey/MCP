"""
Security middleware for MCP API
Adds security headers and protection measures
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware pour ajouter les headers de sécurité"""
    
    def __init__(self, app, is_production: bool = False):
        super().__init__(app)
        self.is_production = is_production
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Traiter la requête
        response = await call_next(request)
        
        # Ajouter les headers de sécurité avec le request en paramètre
        self._add_security_headers(response, request)
        
        return response
    
    def _add_security_headers(self, response: Response, request: Request = None):
        """Ajoute les headers de sécurité à la réponse"""
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self' https://api.dazno.de https://app.dazno.de https://dazno.de",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        permissions_policy = [
            "camera=()",
            "microphone=()",
            "geolocation=()",
            "interest-cohort=()"
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)
        
        # HSTS for production
        if self.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Server identification
        response.headers["Server"] = "MCP-API"
        
        # Cache control for API responses
        if request and request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"