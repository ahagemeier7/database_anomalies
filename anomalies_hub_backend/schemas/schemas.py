from pydantic import BaseModel, Field

class StatusUpdatePayload(BaseModel):
    status: str = Field(..., description="Status ('confirmed_fraud' ou 'false_positive')")

class RetrainResponse(BaseModel):
    message: str