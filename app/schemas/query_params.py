from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from app.exceptions import BadRequestError

class QueryParams(BaseModel):
    model_config = ConfigDict(frozen=True)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_as_none(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

class PeriodParams(QueryParams):
    date_from: date | None = None
    date_to: date | None = None

    def validate_period(self) -> None:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise BadRequestError("date_from must not be after date_to")
