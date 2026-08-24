from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.dependencies import get_db
from app.schemas.complaint_schema import ComplaintRequest
from app.services.analysis_service import AnalysisService
from app.services.ticket_service import TicketService

router = APIRouter(tags=["Intake"])

@router.post("/tickets/analyze-and-create")
def analyze_and_create(request: ComplaintRequest, db: Session = Depends(get_db)):
    analysis, assignment = AnalysisService.analyze(request.complaint_text, request.customer_tier, request.priority, db)
    ticket = TicketService.create_ticket(db, request, analysis, assignment)
    return {"ticket_id": ticket.id, "ticket": ticket, "assignment": assignment["explanation"] if assignment else None}
