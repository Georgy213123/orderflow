from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Material(Base):
    """Справочник материалов и цен. Цена — копейки за единицу, без float."""

    __tablename__ = "materials"
    __table_args__ = (
        CheckConstraint("kind in ('board','back','edge','hardware')", name="ck_material_kind"),
        CheckConstraint("unit in ('m2','m','pcs')", name="ck_material_unit"),
        CheckConstraint("price_kop is null or price_kop >= 0", name="ck_material_price"),
        CheckConstraint("waste_factor >= 1", name="ck_material_waste"),
    )

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(16))
    unit: Mapped[str] = mapped_column(String(8))
    thickness_mm: Mapped[int | None] = mapped_column(Integer)
    price_kop: Mapped[int | None] = mapped_column(BigInteger)
    price_date: Mapped[date | None] = mapped_column(Date)
    waste_factor: Mapped[Decimal] = mapped_column(Numeric(5, 3), default=Decimal("1.000"))


class Request(Base):
    __tablename__ = "requests"
    __table_args__ = (
        CheckConstraint(
            "status in ('new','parsed','designed','estimated','sent')", name="ck_request_status"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="new")
    parser: Mapped[str] = mapped_column(String(16), default="rules")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    fields: Mapped[list["RequestField"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", order_by="RequestField.id"
    )
    design: Mapped["Design | None"] = relationship(
        back_populates="request", cascade="all, delete-orphan", uselist=False
    )
    estimate: Mapped["EstimateRecord | None"] = relationship(
        back_populates="request", cascade="all, delete-orphan", uselist=False
    )
    history: Mapped[list["StatusChange"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", order_by="StatusChange.id"
    )


class RequestField(Base):
    __tablename__ = "request_fields"
    __table_args__ = (
        UniqueConstraint("request_id", "key", name="uq_request_field_key"),
        CheckConstraint("source in ('text','human')", name="ck_field_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(32))
    value: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(8))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    fragment: Mapped[str | None] = mapped_column(String(255))

    request: Mapped[Request] = relationship(back_populates="fields")


class StatusChange(Base):
    __tablename__ = "status_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"))
    from_status: Mapped[str] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped[Request] = relationship(back_populates="history")


class Design(Base):
    __tablename__ = "designs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), unique=True
    )
    params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped[Request] = relationship(back_populates="design")
    parts: Mapped[list["DesignPart"]] = relationship(
        cascade="all, delete-orphan", order_by="DesignPart.position"
    )
    hardware: Mapped[list["DesignHardware"]] = relationship(
        cascade="all, delete-orphan", order_by="DesignHardware.id"
    )


class DesignPart(Base):
    __tablename__ = "design_parts"
    __table_args__ = (
        CheckConstraint("length_mm > 0 and width_mm > 0 and qty > 0", name="ck_part_positive"),
        CheckConstraint("edge_long between 0 and 2 and edge_short between 0 and 2", name="ck_edge"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    design_id: Mapped[int] = mapped_column(ForeignKey("designs.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120))
    length_mm: Mapped[int] = mapped_column(Integer)
    width_mm: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer)
    material_code: Mapped[str] = mapped_column(ForeignKey("materials.code"))
    edge_long: Mapped[int] = mapped_column(Integer, default=0)
    edge_short: Mapped[int] = mapped_column(Integer, default=0)


class DesignHardware(Base):
    __tablename__ = "design_hardware"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    design_id: Mapped[int] = mapped_column(ForeignKey("designs.id", ondelete="CASCADE"))
    material_code: Mapped[str] = mapped_column(ForeignKey("materials.code"))
    name: Mapped[str] = mapped_column(String(120))
    qty: Mapped[int] = mapped_column(Integer)


class EstimateRecord(Base):
    __tablename__ = "estimates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), unique=True
    )
    total_kop: Mapped[int] = mapped_column(BigInteger)
    complete: Mapped[bool] = mapped_column(Boolean)
    totals_by_kind: Mapped[dict[str, int]] = mapped_column(JSONB)
    warnings: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped[Request] = relationship(back_populates="estimate")
    lines: Mapped[list["EstimateLineRecord"]] = relationship(
        cascade="all, delete-orphan", order_by="EstimateLineRecord.position"
    )


class EstimateLineRecord(Base):
    __tablename__ = "estimate_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    estimate_id: Mapped[int] = mapped_column(ForeignKey("estimates.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    material_code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(8))
    net_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    waste_factor: Mapped[Decimal] = mapped_column(Numeric(5, 3))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    price_kop: Mapped[int | None] = mapped_column(BigInteger)
    price_date: Mapped[date | None] = mapped_column(Date)
    amount_kop: Mapped[int | None] = mapped_column(BigInteger)
