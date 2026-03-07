from pydantic import BaseModel


class HealthResponse(BaseModel):
    service: str
    environment: str
    status: str
