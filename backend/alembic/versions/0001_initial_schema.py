"""initial schema

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "materials",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("unit", sa.String(length=8), nullable=False),
        sa.Column("thickness_mm", sa.Integer(), nullable=True),
        sa.Column("price_kop", sa.BigInteger(), nullable=True),
        sa.Column("price_date", sa.Date(), nullable=True),
        sa.Column("waste_factor", sa.Numeric(precision=5, scale=3), nullable=False),
        sa.CheckConstraint("kind in ('board','back','edge','hardware')", name="ck_material_kind"),
        sa.CheckConstraint("unit in ('m2','m','pcs')", name="ck_material_unit"),
        sa.CheckConstraint("price_kop is null or price_kop >= 0", name="ck_material_price"),
        sa.CheckConstraint("waste_factor >= 1", name="ck_material_waste"),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("parser", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('new','parsed','designed','estimated','sent')", name="ck_request_status"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "designs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_table(
        "estimates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("total_kop", sa.BigInteger(), nullable=False),
        sa.Column("complete", sa.Boolean(), nullable=False),
        sa.Column("totals_by_kind", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_table(
        "request_fields",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("fragment", sa.String(length=255), nullable=True),
        sa.CheckConstraint("source in ('text','human')", name="ck_field_source"),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "key", name="uq_request_field_key"),
    )
    op.create_table(
        "status_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=16), nullable=False),
        sa.Column("to_status", sa.String(length=16), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "design_hardware",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("design_id", sa.Integer(), nullable=False),
        sa.Column("material_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["material_code"],
            ["materials.code"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "design_parts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("design_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("length_mm", sa.Integer(), nullable=False),
        sa.Column("width_mm", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("material_code", sa.String(length=32), nullable=False),
        sa.Column("edge_long", sa.Integer(), nullable=False),
        sa.Column("edge_short", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "edge_long between 0 and 2 and edge_short between 0 and 2", name="ck_edge"
        ),
        sa.CheckConstraint("length_mm > 0 and width_mm > 0 and qty > 0", name="ck_part_positive"),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["material_code"],
            ["materials.code"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "estimate_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("estimate_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("material_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("unit", sa.String(length=8), nullable=False),
        sa.Column("net_quantity", sa.Numeric(precision=14, scale=6), nullable=False),
        sa.Column("waste_factor", sa.Numeric(precision=5, scale=3), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("price_kop", sa.BigInteger(), nullable=True),
        sa.Column("price_date", sa.Date(), nullable=True),
        sa.Column("amount_kop", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["estimate_id"], ["estimates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("estimate_lines")
    op.drop_table("design_parts")
    op.drop_table("design_hardware")
    op.drop_table("status_changes")
    op.drop_table("request_fields")
    op.drop_table("estimates")
    op.drop_table("designs")
    op.drop_table("requests")
    op.drop_table("materials")
