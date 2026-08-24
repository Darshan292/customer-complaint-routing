from pydantic import BaseModel


class StatusUpdate(BaseModel):
    status: str


from pydantic import BaseModel, Field


class TicketAssignmentRequest(BaseModel):
    agent_id: int = Field(
        gt=0
    )

class TicketEscalationRequest(BaseModel):

    reason: str

    target: str | None = None