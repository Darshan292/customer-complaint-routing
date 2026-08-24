from typing import Optional

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):

    name: str
    email: str
    password: str

    team: str

    skills: str = ""

    experience_years: float = Field(
        default=0,
        ge=0,
    )

    capacity: int = Field(
        default=10,
        ge=1,
    )

    max_concurrent_tickets: Optional[int] = Field(
        default=None,
        ge=1,
    )

    role: str = "agent"

    availability_status: str = (
        "AVAILABLE"
    )

    timezone: str = "Asia/Kolkata"

    shift_start: str = "09:00"

    shift_end: str = "18:00"

    work_days: str = "0,1,2,3,4"

    auto_assignment_enabled: bool = True


class AgentStatusUpdate(BaseModel):

    availability_status: str


class AgentCapacityUpdate(BaseModel):

    max_concurrent_tickets: int = Field(
        ge=1,
    )


class AgentScheduleUpdate(BaseModel):

    timezone: str
    shift_start: str
    shift_end: str
    work_days: str

class AgentOnCallUpdate(BaseModel):

    on_call_enabled: bool