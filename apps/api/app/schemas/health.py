from pydantic import BaseModel


class ServiceStatus(BaseModel):
    service: str
    environment: str
    status: str


class InfraChecks(BaseModel):
    db: str
    redis: str


class ReadyStatus(BaseModel):
    service: str
    environment: str
    status: str
    checks: InfraChecks
