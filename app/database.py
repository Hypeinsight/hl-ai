"""Database connection management for multi-tenant architecture"""
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from uuid import UUID
from typing import Generator, Dict
import threading

from app.config import settings

# ==================================================================
# REGISTRY DATABASE CONNECTION
# ==================================================================

# Registry database engine (central coordination database)
registry_engine = create_engine(
    settings.REGISTRY_DB_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

RegistrySessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=registry_engine
)


@contextmanager
def get_registry_session() -> Generator[Session, None, None]:
    """
    Get registry database session

    Usage:
        with get_registry_session() as session:
            tenant = session.query(Tenant).filter_by(tenant_key='clinic1').first()
    """
    session = RegistrySessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ==================================================================
# TENANT DATABASE CONNECTION MANAGER
# ==================================================================

class TenantDatabaseManager:
    """
    Manage tenant database connections

    Maintains a pool of database engines for each tenant.
    Thread-safe with locking to prevent race conditions.
    """

    def __init__(self):
        self._engines: Dict[str, any] = {}
        self._lock = threading.Lock()

    def get_tenant_engine(self, tenant_id: UUID):
        """
        Get or create engine for tenant

        Args:
            tenant_id: UUID of the tenant

        Returns:
            SQLAlchemy engine for tenant database

        Raises:
            ValueError: If tenant not found in registry
        """
        key = str(tenant_id)

        # Check if engine already exists
        if key in self._engines:
            return self._engines[key]

        # Create new engine with lock
        with self._lock:
            # Double-check after acquiring lock
            if key in self._engines:
                return self._engines[key]

            # Get tenant metadata from registry
            with get_registry_session() as session:
                from app.models.registry import Tenant
                tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()

                if not tenant:
                    raise ValueError(f"Tenant {tenant_id} not found in registry")

                if tenant.status != 'ACTIVE':
                    raise ValueError(f"Tenant {tenant_id} is not active (status: {tenant.status})")

            # Build database URL
            db_url = (
                f"postgresql://{settings.TENANT_DB_USER}:{settings.TENANT_DB_PASSWORD}"
                f"@{tenant.database_host}:{tenant.database_port}/{tenant.database_name}"
            )

            # Create engine
            engine = create_engine(
                db_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=settings.DEBUG
            )

            self._engines[key] = engine
            return engine

    def get_session_factory(self, tenant_id: UUID):
        """
        Get session factory for tenant

        Args:
            tenant_id: UUID of the tenant

        Returns:
            SQLAlchemy session factory
        """
        engine = self.get_tenant_engine(tenant_id)
        return sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def clear_engine(self, tenant_id: UUID):
        """
        Remove engine from cache (useful when tenant config changes)

        Args:
            tenant_id: UUID of the tenant
        """
        key = str(tenant_id)
        with self._lock:
            if key in self._engines:
                engine = self._engines.pop(key)
                engine.dispose()

    def clear_all_engines(self):
        """Clear all cached engines (useful for cleanup)"""
        with self._lock:
            for engine in self._engines.values():
                engine.dispose()
            self._engines.clear()


# Global tenant manager instance
_tenant_manager = TenantDatabaseManager()


@contextmanager
def get_tenant_session(tenant_id: UUID) -> Generator[Session, None, None]:
    """
    Get tenant database session

    Usage:
        with get_tenant_session(tenant_id) as session:
            messages = session.query(Message).filter_by(status='NEW').all()

    Args:
        tenant_id: UUID of the tenant

    Yields:
        SQLAlchemy session connected to tenant database

    Raises:
        ValueError: If tenant not found or inactive
    """
    SessionLocal = _tenant_manager.get_session_factory(tenant_id)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ==================================================================
# UTILITY FUNCTIONS
# ==================================================================

def test_registry_connection() -> bool:
    """
    Test registry database connection

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_registry_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Registry connection failed: {e}")
        return False


def test_tenant_connection(tenant_id: UUID) -> bool:
    """
    Test tenant database connection

    Args:
        tenant_id: UUID of the tenant

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_tenant_session(tenant_id) as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Tenant {tenant_id} connection failed: {e}")
        return False


def get_all_tenants() -> list:
    """
    Get list of all active tenants

    Returns:
        List of Tenant objects
    """
    with get_registry_session() as session:
        from app.models.registry import Tenant
        return session.query(Tenant).filter(Tenant.status == 'ACTIVE').all()


def create_registry_tables():
    """Create all registry database tables"""
    from app.models.registry import Base
    Base.metadata.create_all(bind=registry_engine)


def create_tenant_tables(tenant_id: UUID):
    """
    Create all tables for a tenant database

    Args:
        tenant_id: UUID of the tenant
    """
    from app.models.tenant import Base
    engine = _tenant_manager.get_tenant_engine(tenant_id)
    Base.metadata.create_all(bind=engine)


def drop_registry_tables():
    """Drop all registry database tables (USE WITH CAUTION!)"""
    from app.models.registry import Base
    Base.metadata.drop_all(bind=registry_engine)


def drop_tenant_tables(tenant_id: UUID):
    """
    Drop all tables for a tenant database (USE WITH CAUTION!)

    Args:
        tenant_id: UUID of the tenant
    """
    from app.models.tenant import Base
    engine = _tenant_manager.get_tenant_engine(tenant_id)
    Base.metadata.drop_all(bind=engine)


# ==================================================================
# CLEANUP
# ==================================================================

def cleanup_connections():
    """Dispose all database connections"""
    registry_engine.dispose()
    _tenant_manager.clear_all_engines()
