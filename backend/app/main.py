"""Punto de entrada FastAPI — ClipAI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.config.settings import get_settings
from app.database.session import Base, SessionLocal, engine
from app.models import Clip, Transcription, User, Video  # noqa: F401 — registra modelos
from app.models import (  # noqa: F401 — modelos SaaS
    AnalyticsSnapshot,
    AutomationSettings,
    Caption,
    ClipContent,
    CreditLedger,
    Job,
    LearningInsight,
    Notification,
    Plan,
    Project,
    ScheduledPost,
    SocialAccount,
    Subscription,
    Thumbnail,
    TrendReport,
)
from app.routes.videos import router as videos_router
from app.utils.exceptions import AppError
from app.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def _ensure_schema_columns() -> None:
    """Añade columnas nuevas si la DB ya existía (create_all no altera)."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    with engine.begin() as conn:
        if "videos" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("videos")}
            if "opciones" not in cols:
                conn.execute(text("ALTER TABLE videos ADD COLUMN opciones JSON NULL"))
                logger.info("Columna videos.opciones añadida")
            if "progreso_detalle" not in cols:
                conn.execute(text("ALTER TABLE videos ADD COLUMN progreso_detalle TEXT NULL"))
                logger.info("Columna videos.progreso_detalle añadida")
            if "eta_segundos" not in cols:
                conn.execute(text("ALTER TABLE videos ADD COLUMN eta_segundos INT NULL"))
                logger.info("Columna videos.eta_segundos añadida")
        if "clips" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("clips")}
            if "formato" not in cols:
                conn.execute(
                    text("ALTER TABLE clips ADD COLUMN formato VARCHAR(32) NULL")
                )
                logger.info("Columna clips.formato añadida")


def _bootstrap_saas() -> None:
    """Planes, créditos y usuario por defecto (id=1)."""
    try:
        from app.modules.credits.service import CreditsService

        db = SessionLocal()
        try:
            CreditsService().bootstrap(db, user_id=1)
            logger.info("Bootstrap SaaS (usuario/créditos) OK")
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Bootstrap SaaS omitido: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    settings.ensure_directories()
    logger.info("ClipAI v%s iniciando…", __version__)

    try:
        Base.metadata.create_all(bind=engine)
        _ensure_schema_columns()
        _bootstrap_saas()
        logger.info("Tablas MySQL verificadas/creadas")
    except SQLAlchemyError as exc:
        logger.error(
            "No se pudo conectar a MySQL (%s). "
            "Verifica .env y que la base '%s' exista.",
            exc,
            settings.mysql_database,
        )
        raise

    # Verificar FFmpeg al arrancar (aviso, no bloquea si falla en imports tardíos)
    try:
        from app.services.dependencies import get_ffmpeg_service

        get_ffmpeg_service()
        logger.info("FFmpeg OK")
    except Exception as exc:  # noqa: BLE001
        logger.warning("FFmpeg no disponible al arranque: %s", exc)

    yield
    logger.info("ClipAI detenido")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ClipAI",
        description="Plataforma local de IA para generación automática de clips de video",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        logger.warning("AppError %s: %s", exc.status_code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(SQLAlchemyError)
    async def db_error_handler(_request: Request, exc: SQLAlchemyError):
        logger.error("MySQL error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Error de base de datos MySQL"},
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__}

    app.include_router(videos_router)

    from app.routes.compose import router as compose_router
    app.include_router(compose_router)

    from app.routes.voices import router as voices_router
    app.include_router(voices_router)

    from app.routes.extract import router as extract_router
    app.include_router(extract_router)

    from app.routes.stories import router as stories_router
    app.include_router(stories_router)

    from app.routes.convert import router as convert_router
    app.include_router(convert_router)

    from app.routes.basic_edit import router as basic_edit_router
    app.include_router(basic_edit_router)

    # Segunda capa SaaS
    from app.modules.dashboard.routes import router as dashboard_router
    from app.modules.library.routes import router as library_router
    from app.modules.content_ai.routes import router as content_router
    from app.modules.thumbnails.routes import router as thumbnails_router
    from app.modules.editor.routes import router as editor_router
    from app.modules.publishing.routes import router as publishing_router
    from app.modules.calendar.routes import router as calendar_router
    from app.modules.analytics.routes import router as analytics_router
    from app.modules.learning.routes import router as learning_router
    from app.modules.automation.routes import router as automation_router
    from app.modules.credits.routes import router as credits_router
    from app.modules.admin.routes import router as admin_router
    from app.modules.trends.routes import router as trends_router
    from app.modules.jobs.routes import router as jobs_router
    from app.modules.growth_agent.routes import router as growth_router
    from app.modules.projects.routes import router as projects_router

    for r in (
        dashboard_router,
        library_router,
        content_router,
        thumbnails_router,
        editor_router,
        publishing_router,
        calendar_router,
        analytics_router,
        learning_router,
        automation_router,
        credits_router,
        admin_router,
        trends_router,
        jobs_router,
        growth_router,
        projects_router,
    ):
        app.include_router(r)

    return app


app = create_app()
