from pydantic import BaseModel, Field
from typing import Optional, Literal


class ComplaintRequest(BaseModel):
    customer_name: str
    customer_tier: str = "Standard"
    complaint_text: str = Field(min_length=10)
    priority: Optional[Literal["Low", "Medium", "High", "Critical"]] = None


class ManualAssignmentRequest(BaseModel):
    agent_id: Optional[int] = None


class StatusUpdate(BaseModel):
    status: Literal["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER", "RESOLVED", "CLOSED"]


class PriorityUpdate(BaseModel):
    priority: Literal["Low", "Medium", "High", "Critical"]
