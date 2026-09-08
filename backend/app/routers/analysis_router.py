from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.ticket_attachment import TicketAttachment
from app.services.analysis_service import AnalysisService
from app.services.ticket_service import TicketService

router = APIRouter(tags=["Intake"])


@router.post("/tickets/analyze-and-create")
def analyze_and_create(
    customer_name: str = Form(...),
    customer_tier: str = Form("Standard"),
    complaint_text: str = Form(...),
    priority: str | None = Form(None),
    attachment: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    if len(complaint_text.strip()) < 10:
        raise HTTPException(400, "Describe the issue in at least 10 characters.")

    normalized_text = complaint_text.lower()
    is_cost_center_request = (
        "cost center" in normalized_text
        and any(word in normalized_text for word in ("creation", "create", "creating"))
    )
    if is_cost_center_request and not attachment:
        raise HTTPException(400, "Attach the prepared Cost Center EIB template for this request.")

    if is_cost_center_request and attachment and not attachment.filename.lower().endswith(".xlsx"):
        raise HTTPException(400, "Cost Center EIB requests require an .xlsx EIB template.")

    if attachment and attachment.filename and attachment.size and attachment.size > 10 * 1024 * 1024:
        raise HTTPException(413, "Attachment exceeds the 10 MB limit.")

    if attachment and not attachment.filename:
        raise HTTPException(400, "The uploaded attachment has no filename.")

    analysis, assignment = AnalysisService.analyze(
        complaint_text, customer_tier, priority, db
    )

    request = type("ComplaintRequestData", (), {
        "customer_name": customer_name,
        "customer_tier": customer_tier,
        "complaint_text": complaint_text,
        "priority": priority,
        "request_type": "WORKDAY_COST_CENTER_EIB" if is_cost_center_request else None,
    })()

    if is_cost_center_request and not assignment:
        raise HTTPException(503, "Priya Nair is not available as the configured Cost Center EIB resolver.")

    ticket = TicketService.create_ticket(db, request, analysis, assignment)

    if attachment:
        content = awaitable_read(attachment)
        db.add(TicketAttachment(
            ticket_id=ticket.id,
            filename=attachment.filename,
            content_type=attachment.content_type or "application/octet-stream",
            file_size=len(content),
            content=content,
        ))
        db.commit()
        db.refresh(ticket)

    return {
        "ticket_id": ticket.id,
        "ticket": ticket,
        "assignment": assignment["explanation"] if assignment else None,
    }


def awaitable_read(upload: UploadFile) -> bytes:
    # UploadFile.read() is async; this helper exists only to keep the endpoint
    # body readable without changing the rest of the service layer.
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # Endpoint is sync, so FastAPI normally gives us a SpooledTemporaryFile.
            return upload.file.read()
    except RuntimeError:
        pass
    return upload.file.read()
