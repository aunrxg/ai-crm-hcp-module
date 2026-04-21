from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from app.config import settings

print(f"DEBUG: Connecting to {settings.database_url}") # ADD THIS
engine = create_engine(settings.database_url, future=True)
print(f"DEBUG: Engine created") # ADD THIS
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
print(f"DEBUG: SessionLocal created") # ADD THIS
def check_db_connection() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        print(f"DEBUG: Connection successful") # ADD THIS
    return True
