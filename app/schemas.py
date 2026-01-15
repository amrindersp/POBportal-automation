from pydantic import BaseModel, Field

class AutomationStartRequest(BaseModel):
    mail_username: str = Field(..., min_length=3)
    mail_password: str = Field(..., min_length=3)
    pob_username: str = Field(..., min_length=3)
    pob_password: str = Field(..., min_length=3)
    email_id: str
    vessel: str

class AutomationStatusResponse(BaseModel):
    run_id: int
    step: str
    status: str
    message: str | None = None

