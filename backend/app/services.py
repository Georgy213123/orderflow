"""Сценарии: заявка → разбор → конструкция → смета → отправка.

Каждая операция, меняющая статус, проходит через `_move`: там сервер проверяет переход.
"""

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.design import CabinetParams, DesignError, Specification, build_specification
from app.domain.estimate import MaterialPrice, UnknownMaterialError, build_estimate
from app.domain.fields import (
    FIELD_LABELS,
    INT_FIELDS,
    REQUIRED_FIELDS,
    FieldKey,
    FieldSource,
    FieldState,
    apply_human_input,
    missing_for_parsed,
)
from app.domain.money import format_kop
from app.domain.parser import RequestParser
from app.domain.status import STATUS_LABELS, RequestStatus, TransitionError, check_transition
from app.integrations.notifier import ClientNotifier
from app.models import (
    Design,
    DesignHardware,
    DesignPart,
    EstimateLineRecord,
    EstimateRecord,
    Material,
    Request,
    RequestField,
    StatusChange,
)
from app.schemas import (
    DesignOut,
    DesignParamsIn,
    EstimateLineOut,
    EstimateOut,
    FieldOut,
    HardwareOut,
    PartOut,
    RequestOut,
    RequestSummary,
    StatusChangeOut,
)

MAX_FIELD_LEN = 255


class DomainError(Exception):
    def __init__(self, status_code: int, message: str, problems: list[str] | None = None) -> None:
        self.status_code = status_code
        self.message = message
        self.problems = problems or []
        super().__init__(message)


def _not_found(what: str) -> DomainError:
    return DomainError(404, f"{what} не найдена")


# ---------- заявка и поля ----------


def _states(req: Request) -> dict[FieldKey, FieldState]:
    return {
        FieldKey(f.key): FieldState(f.value, FieldSource(f.source), f.confirmed, f.fragment)
        for f in req.fields
    }


def request_out(req: Request) -> RequestOut:
    status = RequestStatus(req.status)
    order = {k: i for i, k in enumerate(FieldKey)}
    fields = sorted(req.fields, key=lambda f: order[FieldKey(f.key)])
    return RequestOut(
        id=req.id,
        raw_text=req.raw_text,
        status=status,
        status_label=STATUS_LABELS[status],
        parser=req.parser,
        created_at=req.created_at,
        fields=[
            FieldOut(
                key=FieldKey(f.key),
                label=FIELD_LABELS[FieldKey(f.key)],
                value=f.value,
                source=FieldSource(f.source),
                confirmed=f.confirmed,
                fragment=f.fragment,
                required=FieldKey(f.key) in REQUIRED_FIELDS,
            )
            for f in fields
        ],
        missing=missing_for_parsed(_states(req)),
        history=[
            StatusChangeOut(
                from_status=RequestStatus(h.from_status),
                to_status=RequestStatus(h.to_status),
                changed_at=h.changed_at,
            )
            for h in req.history
        ],
    )


def _load(session: Session, request_id: int, *, lock: bool = False) -> Request:
    """Заявка с полями и историей. `lock=True` — блокировка строки до конца транзакции:
    все операции, меняющие заявку, идут по ней последовательно (R-03, R-05 ревью)."""
    query = (
        select(Request)
        .where(Request.id == request_id)
        .options(selectinload(Request.fields), selectinload(Request.history))
    )
    if lock:
        query = query.with_for_update(of=Request)
    req = session.scalar(query)
    if req is None:
        raise _not_found("заявка")
    return req


def _validate_value(key: FieldKey, value: str) -> str:
    value = value.strip()
    if key in INT_FIELDS and value and not value.isdigit():
        raise DomainError(422, "неверное значение поля", [f"{FIELD_LABELS[key]}: нужно целое"])
    return value


def create_request(
    session: Session, parser: RequestParser, raw_text: str, manual: dict[FieldKey, str]
) -> Request:
    req = Request(raw_text=raw_text, status=RequestStatus.NEW.value, parser=parser.name)
    parsed = parser.parse(raw_text) if raw_text.strip() else {}
    for key, pf in parsed.items():
        if key in manual or len(pf.value) > MAX_FIELD_LEN:
            continue  # значение длиннее колонки — не предположение, а мусор (R-06)
        req.fields.append(
            RequestField(
                key=key.value,
                value=pf.value,
                source=FieldSource.TEXT.value,
                confirmed=False,
                fragment=pf.fragment[:255],
            )
        )
    for key, value in manual.items():
        clean = _validate_value(key, value)
        if clean:
            req.fields.append(
                RequestField(
                    key=key.value, value=clean, source=FieldSource.HUMAN.value, confirmed=True
                )
            )
    session.add(req)
    session.commit()
    return _load(session, req.id)


def list_requests(session: Session) -> list[RequestSummary]:
    reqs = session.scalars(
        select(Request).options(selectinload(Request.fields)).order_by(Request.id.desc())
    ).all()
    out = []
    for r in reqs:
        values = {f.key: f.value for f in r.fields}
        status = RequestStatus(r.status)
        out.append(
            RequestSummary(
                id=r.id,
                status=status,
                status_label=STATUS_LABELS[status],
                client_name=values.get(FieldKey.CLIENT_NAME.value),
                product_type=values.get(FieldKey.PRODUCT_TYPE.value),
                created_at=r.created_at,
            )
        )
    return out


def get_request(session: Session, request_id: int) -> Request:
    return _load(session, request_id)


def update_field(session: Session, request_id: int, key: FieldKey, value: str) -> Request:
    req = _load(session, request_id, lock=True)
    if req.status != RequestStatus.NEW.value:
        raise DomainError(409, "поля правятся только в новой заявке")
    clean = _validate_value(key, value)
    record = next((f for f in req.fields if f.key == key.value), None)
    current = (
        FieldState(record.value, FieldSource(record.source), record.confirmed, record.fragment)
        if record
        else None
    )
    if not clean:
        # Пустое значение — человек убрал поле (например, ошибочно найденную почту).
        if record is not None:
            req.fields.remove(record)
        session.commit()
        return _load(session, request_id)
    new = apply_human_input(current, clean)
    if record is None:
        record = RequestField(key=key.value, value="", source=new.source.value)
        req.fields.append(record)
    record.value = new.value
    record.source = new.source.value
    record.confirmed = new.confirmed
    record.fragment = new.fragment
    session.commit()
    return _load(session, request_id)


def _move(session: Session, req: Request, target: RequestStatus) -> None:
    current = RequestStatus(req.status)
    try:
        check_transition(current, target)
    except TransitionError as e:
        raise DomainError(409, e.reason) from e
    if current != target:
        req.history.append(StatusChange(from_status=current.value, to_status=target.value))
    req.status = target.value


def transition(
    session: Session, notifier: ClientNotifier, request_id: int, target: RequestStatus
) -> Request:
    req = _load(session, request_id, lock=True)
    if target == RequestStatus.PARSED:
        missing = missing_for_parsed(_states(req))
        if missing:
            raise DomainError(409, "заявка не разобрана до конца", missing)
    elif target == RequestStatus.SENT:
        est = session.scalar(select(EstimateRecord).where(EstimateRecord.request_id == req.id))
        if est is None or not est.complete:
            raise DomainError(409, "смета неполная: отправлять клиенту нельзя")
        values = {f.key: f.value for f in req.fields}
        contact = values.get(FieldKey.EMAIL.value) or values.get(FieldKey.PHONE.value, "")
        _move(session, req, target)
        session.commit()
        # Уведомление — после фиксации статуса: при откате транзакции клиент не получит
        # смету, а повторный запрос под блокировкой увидит «отправлена» и получит 409.
        notifier.send_estimate(req.id, contact, est.total_kop)
        return _load(session, request_id)
    elif target in (RequestStatus.DESIGNED, RequestStatus.ESTIMATED):
        raise DomainError(409, "этот статус ставится сохранением конструкции или расчётом сметы")
    _move(session, req, target)
    session.commit()
    return _load(session, request_id)


# ---------- конструкция ----------


def _prices(session: Session) -> dict[str, Material]:
    return {m.code: m for m in session.scalars(select(Material))}


def _check_materials(p: CabinetParams, materials: dict[str, Material]) -> list[str]:
    problems: list[str] = []
    expected = [
        (p.board_code, "board", "плита корпуса"),
        (p.edge_code, "edge", "кромка"),
        (p.handle_code, "hardware", "ручка"),
    ]
    if p.back_panel:
        expected.append((p.back_code, "back", "задняя стенка"))
    for code, kind, label in expected:
        m = materials.get(code)
        if m is None:
            problems.append(f"{label}: материала {code} нет в справочнике")
        elif m.kind != kind:
            problems.append(f"{label}: материал {code} другого вида ({m.kind})")
    board = materials.get(p.board_code)
    if board is not None and board.thickness_mm not in (None, p.thickness_mm):
        problems.append(
            f"плита {p.board_code} толщиной {board.thickness_mm} мм, "
            f"а в конструкции {p.thickness_mm} мм"
        )
    return problems


def design_out(req_id: int, design: Design) -> DesignOut:
    params = DesignParamsIn(**design.params)
    return DesignOut(
        request_id=req_id,
        params=params,
        inner_width_mm=params.width_mm - 2 * params.thickness_mm,
        parts=[PartOut.model_validate(p) for p in design.parts],
        hardware=[HardwareOut.model_validate(h) for h in design.hardware],
    )


def save_design(session: Session, request_id: int, params_in: DesignParamsIn) -> DesignOut:
    req = _load(session, request_id, lock=True)
    if req.status not in (
        RequestStatus.PARSED.value,
        RequestStatus.DESIGNED.value,
        RequestStatus.ESTIMATED.value,
    ):
        raise DomainError(409, "конструкцию задают после разбора заявки")
    params = CabinetParams(**params_in.model_dump())
    problems = _check_materials(params, _prices(session))
    if problems:
        raise DomainError(422, "материалы не подходят", problems)
    try:
        spec = build_specification(params)
    except DesignError as e:
        raise DomainError(422, "конструкция не проходит проверку", e.problems) from e

    old = session.scalar(select(Design).where(Design.request_id == req.id))
    if old is not None:
        session.delete(old)
    old_est = session.scalar(select(EstimateRecord).where(EstimateRecord.request_id == req.id))
    if old_est is not None:
        session.delete(old_est)  # конструкция изменилась — смета устарела
    session.flush()

    design = Design(request_id=req.id, params=asdict(params))
    for i, part in enumerate(spec.parts):
        design.parts.append(
            DesignPart(
                position=i,
                code=part.code,
                name=part.name,
                length_mm=part.length_mm,
                width_mm=part.width_mm,
                qty=part.qty,
                material_code=part.material_code,
                edge_long=part.edge_long,
                edge_short=part.edge_short,
            )
        )
    for item in spec.hardware:
        design.hardware.append(
            DesignHardware(material_code=item.material_code, name=item.name, qty=item.qty)
        )
    session.add(design)
    _move(session, req, RequestStatus.DESIGNED)
    session.commit()
    return design_out(req.id, design)


def get_design(session: Session, request_id: int) -> DesignOut:
    _load(session, request_id)
    design = session.scalar(
        select(Design)
        .where(Design.request_id == request_id)
        .options(selectinload(Design.parts), selectinload(Design.hardware))
    )
    if design is None:
        raise _not_found("конструкция")
    return design_out(request_id, design)


# ---------- смета ----------


def _spec_from_design(design: Design) -> Specification:
    from app.domain.design import HardwareItem, Part

    return Specification(
        parts=[
            Part(
                p.code,
                p.name,
                p.length_mm,
                p.width_mm,
                p.qty,
                p.material_code,
                p.edge_long,
                p.edge_short,
            )
            for p in design.parts
        ],
        hardware=[HardwareItem(h.material_code, h.name, h.qty) for h in design.hardware],
        edge_code=str(design.params["edge_code"]),
    )


def estimate_out(rec: EstimateRecord) -> EstimateOut:
    return EstimateOut(
        request_id=rec.request_id,
        lines=[EstimateLineOut.model_validate(ln) for ln in rec.lines],
        totals_by_kind=rec.totals_by_kind,
        total_kop=rec.total_kop,
        total_formatted=format_kop(rec.total_kop),
        complete=rec.complete,
        warnings=rec.warnings,
        created_at=rec.created_at,
    )


def calculate_estimate(session: Session, request_id: int) -> EstimateOut:
    req = _load(session, request_id, lock=True)
    design = session.scalar(
        select(Design)
        .where(Design.request_id == req.id)
        .options(selectinload(Design.parts), selectinload(Design.hardware))
    )
    if design is None:
        raise DomainError(409, "сначала задайте конструкцию")
    _move(session, req, RequestStatus.ESTIMATED)
    prices = {
        code: MaterialPrice(
            m.code, m.name, m.kind, m.unit, m.price_kop, m.price_date, m.waste_factor
        )
        for code, m in _prices(session).items()
    }
    try:
        est = build_estimate(_spec_from_design(design), prices)
    except UnknownMaterialError as e:
        raise DomainError(422, str(e)) from e

    old = session.scalar(select(EstimateRecord).where(EstimateRecord.request_id == req.id))
    if old is not None:
        session.delete(old)
        session.flush()
    rec = EstimateRecord(
        request_id=req.id,
        total_kop=est.total_kop,
        complete=est.complete,
        totals_by_kind=est.totals_by_kind,
        warnings=est.warnings,
    )
    for i, ln in enumerate(est.lines):
        rec.lines.append(
            EstimateLineRecord(
                position=i,
                kind=ln.kind,
                material_code=ln.material_code,
                name=ln.name,
                unit=ln.unit,
                net_quantity=ln.net_quantity,
                waste_factor=ln.waste_factor,
                quantity=ln.quantity,
                price_kop=ln.price_kop,
                price_date=ln.price_date,
                amount_kop=ln.amount_kop,
            )
        )
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return estimate_out(rec)


def get_estimate(session: Session, request_id: int) -> EstimateOut:
    _load(session, request_id)
    rec = session.scalar(
        select(EstimateRecord)
        .where(EstimateRecord.request_id == request_id)
        .options(selectinload(EstimateRecord.lines))
    )
    if rec is None:
        raise _not_found("смета")
    return estimate_out(rec)


def list_materials(session: Session) -> list[Material]:
    return list(session.scalars(select(Material).order_by(Material.kind, Material.code)))
