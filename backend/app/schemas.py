from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.domain.fields import FieldKey, FieldSource
from app.domain.status import RequestStatus


class Problem(BaseModel):
    """Ошибка предметной области: что не так и список конкретных причин."""

    message: str
    problems: list[str] = Field(default_factory=list)


class FieldOut(BaseModel):
    key: FieldKey
    label: str
    value: str
    source: FieldSource
    confirmed: bool
    fragment: str | None
    required: bool


class StatusChangeOut(BaseModel):
    from_status: RequestStatus
    to_status: RequestStatus
    changed_at: datetime


class RequestOut(BaseModel):
    id: int
    raw_text: str
    status: RequestStatus
    status_label: str
    parser: str
    created_at: datetime
    fields: list[FieldOut]
    missing: list[str] = Field(description="Что мешает перевести заявку в «разобрана»")
    history: list[StatusChangeOut]


class RequestSummary(BaseModel):
    id: int
    status: RequestStatus
    status_label: str
    client_name: str | None
    product_type: str | None
    created_at: datetime


FieldValue = Annotated[str, Field(max_length=255)]


class RequestCreate(BaseModel):
    raw_text: str = Field("", max_length=5000, description="Свободный текст заявки")
    fields: dict[FieldKey, FieldValue] = Field(
        default_factory=dict, description="Поля, введённые человеком вручную"
    )


class FieldUpdate(BaseModel):
    value: FieldValue


class TransitionIn(BaseModel):
    to: RequestStatus


class DesignParamsIn(BaseModel):
    width_mm: int = Field(ge=1, le=10_000)
    height_mm: int = Field(ge=1, le=10_000)
    depth_mm: int = Field(ge=1, le=10_000)
    thickness_mm: int = 16
    shelves: int = Field(0, ge=0)
    doors: int = Field(0, ge=0)
    back_panel: bool = True
    board_code: str = "LDSP16-WHITE"
    edge_code: str = "EDGE04-WHITE"
    back_code: str = "HDF3-WHITE"
    handle_code: str = "HW-HANDLE"


class PartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    length_mm: int
    width_mm: int
    qty: int
    material_code: str
    edge_long: int
    edge_short: int


class HardwareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    material_code: str
    name: str
    qty: int


class DesignOut(BaseModel):
    request_id: int
    params: DesignParamsIn
    inner_width_mm: int
    parts: list[PartOut]
    hardware: list[HardwareOut]


class EstimateLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    material_code: str
    name: str
    unit: str
    net_quantity: Decimal
    waste_factor: Decimal
    quantity: Decimal
    price_kop: int | None
    price_date: date | None
    amount_kop: int | None


class EstimateOut(BaseModel):
    request_id: int
    lines: list[EstimateLineOut]
    totals_by_kind: dict[str, int]
    total_kop: int
    total_formatted: str
    complete: bool
    warnings: list[str]
    created_at: datetime


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    kind: str
    unit: str
    thickness_mm: int | None
    price_kop: int | None
    price_date: date | None
    waste_factor: Decimal


class Health(BaseModel):
    status: str
    parser: str
