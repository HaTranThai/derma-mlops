import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_current_user
from app.api.routers import admin, auth, health, monitoring, predict, predictions, reviews
from app.db.database import pool
from app.db.init_db import init_db
from app.repositories import user_repository
from app.services import auto_trigger
from app.services.gradcam_service import GradCAM
from app.services.model_service import ModelService
from app.services.storage_service import StorageService

logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        pool.open()
    except Exception as err:
        logger.warning("Khong mo duoc connection pool: %s", err)

    app.state.storage = None
    for attempt in range(1, 11):
        try:
            init_db()
            user_repository.seed_users()
            app.state.storage = StorageService()
            logger.info("PostgreSQL + MinIO san sang.")
            break
        except Exception as err:
            logger.warning("Khoi tao DB/MinIO lan %s that bai: %s", attempt, err)
            time.sleep(3)

    app.state.model_service = None
    app.state.gradcam = None
    for attempt in range(1, 6):
        try:
            model_service = ModelService()
            app.state.model_service = model_service
            app.state.gradcam = GradCAM(model_service.model, model_service.target_layer)
            logger.info("Model loaded tu MinIO: %s (%s)", model_service.model_version, model_service.source)
            break
        except Exception as err:
            logger.warning("Nap model tu MinIO lan %s that bai: %s", attempt, err)
            time.sleep(3)
    if app.state.model_service is None:
        logger.warning("Chua co model Production trong MinIO (models/production/model.pt).")

    trigger_task = asyncio.create_task(auto_trigger.loop())

    yield

    trigger_task.cancel()
    try:
        pool.close()
    except Exception:
        pass


app = FastAPI(title="Skin Lesion Classifier API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(predict.router, dependencies=[Depends(get_current_user)])
app.include_router(predictions.router)
app.include_router(reviews.router, dependencies=[Depends(get_current_user)])
app.include_router(monitoring.router)
app.include_router(admin.router)
