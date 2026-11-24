"""Database connection, session factory, tenant isolation, and soft delete hooks."""
import os
from contextvars import ContextVar
from typing import Optional, List
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session, ORMExecuteState, with_loader_criteria
from app.config import settings

# Engine configuration depending on dialect
connect_args = {}
db_url = settings.DATABASE_URL
if os.environ.get("VERCEL") and db_url.startswith("sqlite:///."):
    db_url = "sqlite:////tmp/hotel_pms.db"

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

# Context variables for thread-local request tenant and soft delete state
current_org_id: ContextVar[Optional[int]] = ContextVar("current_org_id", default=None)
include_deleted_records: ContextVar[bool] = ContextVar("include_deleted_records", default=False)


_cached_tenant_models = None
_cached_soft_delete_models = None


def _get_tenant_models():
    global _cached_tenant_models
    if _cached_tenant_models is None:
        from app import models
        _cached_tenant_models = [
            models.RoomType,
            models.Room,
            models.Guest,
            models.Reservation,
            models.Folio,
            models.FolioItem,
            models.Payment,
            models.RatePlan,
            models.CancellationPolicy,
            models.TaxRate,
            models.RateOverride,
            models.HousekeepingTask,
            models.BookingGroup,
            models.GroupBlock,
            models.BusinessDate,
            models.DailySnapshot,
            models.ActivityLog,
            models.EmailTemplate,
            models.InvoiceLog,
            models.BackupRecord,
            models.ExportJob,
            models.AuditLog,
        ]
    return _cached_tenant_models


def _get_soft_delete_models():
    global _cached_soft_delete_models
    if _cached_soft_delete_models is None:
        from app import models
        _cached_soft_delete_models = [
            models.RoomType,
            models.Room,
            models.Guest,
            models.Reservation,
            models.Folio,
            models.FolioItem,
            models.Payment,
            models.RatePlan,
            models.CancellationPolicy,
            models.TaxRate,
            models.BookingGroup,
        ]
    return _cached_soft_delete_models


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_isolation_and_soft_delete(execute_state: ORMExecuteState):
    """SQLAlchemy event hook injecting tenant and soft-delete criteria into queries."""
    if execute_state.is_select:
        # Row-level tenant isolation
        if not execute_state.execution_options.get("ignore_tenant", False):
            active_org = current_org_id.get()
            if active_org is not None:
                for cls in _get_tenant_models():
                    execute_state.statement = execute_state.statement.options(
                        with_loader_criteria(cls, cls.organization_id == active_org, include_aliases=True)
                    )

        # Soft delete filtering
        if not execute_state.execution_options.get("include_deleted", False) and not include_deleted_records.get():
            for cls in _get_soft_delete_models():
                execute_state.statement = execute_state.statement.options(
                    with_loader_criteria(cls, cls.deleted_at.is_(None), include_aliases=True)
                )


def get_db():
    """Dependency that provides an isolated database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
