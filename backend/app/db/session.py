from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings
from backend.app.core.logging import logger

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Apply WAL mode and foreign key constraints for SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_database_connection() -> dict:
    """Verifies SQLite/SQLAlchemy connectivity and returns engine details."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.scalar()

            is_sqlite = settings.DATABASE_URL.startswith("sqlite")
            wal_enabled = False

            if is_sqlite:
                wal_check = connection.execute(text("PRAGMA journal_mode")).scalar()
                wal_enabled = str(wal_check).lower() == "wal"

            return {
                "status": "CONNECTED",
                "engine": "sqlite" if is_sqlite else "postgresql",
                "wal_mode": wal_enabled
            }
    except Exception as exc:
        logger.error(f"Database connection verification failed: {exc}")
        return {
            "status": "DISCONNECTED",
            "error": str(exc)
        }


def init_db():
    """Initializes tables and seeds default policies."""
    import backend.app.models  # Ensure models are imported
    Base.metadata.create_all(bind=engine)

    # Ensure SQLite columns exist for orders if connecting to pre-existing database
    try:
        with engine.connect() as conn:
            existing_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(orders)")).fetchall()]
            if existing_cols:
                if "is_demo_order" not in existing_cols:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN is_demo_order BOOLEAN DEFAULT 0"))
                    conn.commit()
                if "demo_session_id" not in existing_cols:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN demo_session_id VARCHAR(64) DEFAULT NULL"))
                    conn.commit()
    except Exception as e:
        logger.warning(f"Note on order table schema inspection: {e}")

    from backend.app.models.order import SystemPolicy
    db = SessionLocal()
    try:
        default_policies = [
            ("MAX_RETRIES_API_5XX", "Maximum Retries for HTTP 5xx Errors", "RETRY", "INTEGER", "3", "Maximum number of retries authorized after initial technical failure."),
            ("BACKOFF_BASE_SECONDS", "Backoff Base Delay Seconds", "RETRY", "INTEGER", "1", "Base delay in seconds for exponential backoff retry calculation."),
            ("SLA_STAGE_CUSTOMER_ORDER_MS", "Customer Order Ingestion SLA", "SLA", "INTEGER", "1000", "Illustrative demo SLA for customer order ingestion."),
            ("SLA_STAGE_ADDRESS_VALIDATION_MS", "Address Validation SLA", "SLA", "INTEGER", "2000", "Illustrative demo SLA for address verification."),
            ("SLA_STAGE_PAYMENT_MS", "Payment Processing SLA", "SLA", "INTEGER", "3000", "Illustrative demo SLA for payment authorization and capture."),
            ("SLA_STAGE_INVENTORY_MS", "Inventory Reservation SLA", "SLA", "INTEGER", "2000", "Illustrative demo SLA for warehouse inventory reservation."),
            ("SLA_STAGE_FULFILMENT_MS", "Warehouse Fulfilment SLA", "SLA", "INTEGER", "5000", "Illustrative demo SLA for warehouse picking and packing."),
            ("SLA_STAGE_DELIVERY_MS", "Carrier Logistics SLA", "SLA", "INTEGER", "5000", "Illustrative demo SLA for carrier waybill generation."),
            ("SLA_STAGE_NOTIFICATION_MS", "Customer Notification SLA", "SLA", "INTEGER", "1000", "Illustrative demo SLA for confirmation dispatch."),
        ]

        for key, name, cat, vtype, val, desc in default_policies:
            existing = db.query(SystemPolicy).filter_by(policy_key=key).first()
            if not existing:
                policy = SystemPolicy(
                    policy_key=key,
                    policy_name=name,
                    category=cat,
                    value_type=vtype,
                    policy_value=val,
                    description=desc
                )
                db.add(policy)
        db.commit()
        logger.info("Database initialized and default system policies verified.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        db.close()
