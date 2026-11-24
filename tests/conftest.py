"""Pytest Configuration and Fixtures with Fresh In-Memory SQLite Database."""
import os
import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import date, timedelta
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force test environment variables before importing app
os.environ["ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-with-over-thirty-two-chars-for-testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.auth import get_password_hash, create_access_token
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import (
    ActivityLog,
    FolioItem,
    Guest,
    HousekeepingTask,
    Payment,
    Reservation,
    Room,
    RoomType,
    User,
)

# In-memory test engine with StaticPool so all connections share the same memory DB
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides a pristine, fresh in-memory database session for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Provides an AsyncClient bound to the FastAPI app with test db override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seed_test_data(db_session):
    """Populates basic test fixtures: admin user, staff user, room types, rooms, guest."""
    # 1. Users
    admin = User(
        email="admin@test.com",
        username="admin",
        full_name="Admin User",
        hashed_password=get_password_hash("admin123"),
        role="admin",
        is_active=True,
    )
    staff = User(
        email="staff@test.com",
        username="staff",
        full_name="Staff User",
        hashed_password=get_password_hash("staff123"),
        role="front_desk",
        is_active=True,
    )
    db_session.add_all([admin, staff])
    db_session.commit()

    # 2. Room Types
    rt_std = RoomType(
        name="Standard Queen",
        code="STD-Q",
        description="Standard Queen Room",
        base_rate=Decimal("129.00"),
        max_occupancy=2,
    )
    rt_dlx = RoomType(
        name="Deluxe King",
        code="DLX-K",
        description="Deluxe King Room",
        base_rate=Decimal("189.00"),
        max_occupancy=2,
    )
    db_session.add_all([rt_std, rt_dlx])
    db_session.commit()

    # 3. Rooms
    r101 = Room(number="101", floor=1, room_type_id=rt_std.id, status="available")
    r102 = Room(number="102", floor=1, room_type_id=rt_std.id, status="available")
    r201 = Room(number="201", floor=2, room_type_id=rt_dlx.id, status="available")
    db_session.add_all([r101, r102, r201])
    db_session.commit()

    # 4. Guest
    guest = Guest(
        first_name="Priya",
        last_name="Sharma",
        email="priya.sharma@example.com",
        phone="+15551234567",
        address="100 Market St",
        id_number="PASSPORT-1234",
    )
    db_session.add(guest)
    db_session.commit()

    return {
        "admin": admin,
        "staff": staff,
        "rt_std": rt_std,
        "rt_dlx": rt_dlx,
        "r101": r101,
        "r102": r102,
        "r201": r201,
        "guest": guest,
    }


def make_auth_headers(username: str = "admin", role: str = "admin", org_id: int = None) -> dict:
    """Helper creating Bearer Authorization header for test requests."""
    data = {"sub": username, "role": role}
    if org_id is not None:
        data["org_id"] = org_id
    token = create_access_token(data=data)
    headers = {"Authorization": f"Bearer {token}"}
    if org_id is not None:
        headers["X-Organization-Id"] = str(org_id)
    return headers
