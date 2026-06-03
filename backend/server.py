"""Kronikler: Küllerin Mirası — main FastAPI app."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from auth_routes import build_auth_router
from game_routes import build_game_router


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Kronikler: Küllerin Mirası API")


@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.game_states.create_index("user_id", unique=True)
    logger.info("DB indexes ready")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


@app.get("/api/")
async def root():
    return {"app": "Kronikler: Küllerin Mirası", "status": "ok"}


app.include_router(build_auth_router(db))
app.include_router(build_game_router(db))

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
