from pydantic import BaseModel

class VisitCountResponse(BaseModel):
    count: int
