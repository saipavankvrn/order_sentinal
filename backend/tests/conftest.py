import os
import sys
import tempfile
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Ensure workspace root is in sys.path
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

# 1. Create an isolated temporary SQLite database for automated test suite execution
test_db_fd, test_db_path = tempfile.mkstemp(suffix=".db", prefix="test_orderflow_")
os.close(test_db_fd)
test_db_url = f"sqlite:///{test_db_path}"

# 2. Override environment variable and settings BEFORE app and session modules initialize
os.environ["DATABASE_URL"] = test_db_url

from backend.app.core.config import settings
settings.DATABASE_URL = test_db_url

import backend.app.db.session as db_session

# Create isolated test engine with SQLite foreign keys and WAL mode
test_engine = create_engine(
    test_db_url,
    connect_args={"check_same_thread": False},
    echo=False
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


# Rebind engine and SessionLocal in db_session module so all imports and routes use test DB
db_session.engine = test_engine
db_session.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# 3. Initialize schema and default system policies on the isolated test database
from backend.app.db.session import init_db
init_db()

from backend.app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def cleanup_isolated_test_db():
    yield
    # Dispose engine connection pool before deleting files
    test_engine.dispose()
    for ext in ["", "-shm", "-wal"]:
        fpath = test_db_path + ext
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass
