from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.startup_banner import log_startup_banner


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log_startup_banner()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Agentic Enterprise API RAG Backend",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": settings.APP_NAME,
        "docs": "/docs",
        "health": "/api/v1/health",
        "status": "/api/v1/status (admin/super_admin only, Bearer token)",
    }


@app.get("/debug/routes")
def debug_routes():
    return [
        {
            "path": route.path,
            "name": route.name,
            "methods": list(route.methods) if route.methods else [],
        }
        for route in app.routes
    ]
