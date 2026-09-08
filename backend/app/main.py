from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.db import engine, Base
from app.models.complaint import Complaint
from app.models.user import User
from app.models.agent import Agent
from app.models.team import Team
from app.models.ticket_event import TicketEvent
from app.models.notification import Notification
from app.models.ticket_attachment import TicketAttachment
from app.routers.ticket_router import router as ticket_router
from app.routers.analysis_router import router as analysis_router
from app.routers.auth_router import router as auth_router
from app.routers.agent_router import router as agent_router
from app.routers.notification_router import router as notification_router
from app.routers.retrieval_router import router as retrieval_router

app = FastAPI(title="Enterprise Complaint Operations Platform", version="2.0.0")
Base.metadata.create_all(bind=engine)

# Lightweight migration for the temporary integration marker.
# create_all() does not add columns to an existing SQLite table.
with engine.begin() as connection:
    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(complaints)").fetchall()}
    if "request_type" not in columns:
        connection.exec_driver_sql("ALTER TABLE complaints ADD COLUMN request_type VARCHAR")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(analysis_router, prefix="/api")
app.include_router(ticket_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(notification_router, prefix="/api")
app.include_router(retrieval_router, prefix="/api")

@app.get("/")
def health():
    return {"status":"running", "service":"enterprise-complaint-operations", "version":"2.0.0"}
