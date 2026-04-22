from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
import app.models  # noqa: F401
from app.routes.chat import router as chat_router
from app.routes.hcp import router as hcp_router
from app.routes.interactions import router as interactions_router

app = FastAPI(title="AI CRM HCP Module API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hcp_router)
app.include_router(interactions_router)
app.include_router(chat_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok", "model": settings.groq_primary_model}


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
