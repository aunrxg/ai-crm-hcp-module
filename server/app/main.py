from fastapi import FastAPI, HTTPException

from app.database import check_db_connection

app = FastAPI(title="AI CRM HCP API")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "FastAPI server is running"}


@app.get("/health/db")
def db_health() -> dict[str, str]:
    try:
        print("DEBUG: Checking database connection") # ADD THIS
        check_db_connection()
        print("DEBUG: Database connection successful") # ADD THIS
        return {"status": "ok"}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Database connection failed: {exc}")
