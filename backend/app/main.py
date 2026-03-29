from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_db
from app.api.routes import ingest, runs, projects, analytics, ws

# Import all adapters to register them
import app.adapters.playwright   # noqa
import app.adapters.cypress      # noqa
import app.adapters.all_adapters # noqa


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="NexusReport API",
    description="Universal test reporting platform",
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(ingest.router,    prefix=settings.api_prefix, tags=["Ingest"])
app.include_router(runs.router,      prefix=settings.api_prefix, tags=["Runs"])
app.include_router(projects.router,  prefix=settings.api_prefix, tags=["Projects"])
app.include_router(analytics.router, prefix=settings.api_prefix, tags=["Analytics"])
app.include_router(ws.router,        tags=["WebSocket"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.version}
