from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app import services
from app.db import get_session
from app.domain.fields import FieldKey
from app.domain.parser import RequestParser
from app.integrations.notifier import ClientNotifier
from app.schemas import (
    DesignOut,
    DesignParamsIn,
    EstimateOut,
    FieldUpdate,
    Health,
    MaterialOut,
    Problem,
    RequestCreate,
    RequestOut,
    RequestSummary,
    TransitionIn,
)

E422_ALL: dict[int | str, dict[str, Any]] = {
    422: {"model": Problem, "description": "Неверный запрос или данные не проходят проверку"}
}
# Обработчик RequestValidationError отвечает в формате Problem, контракт должен это
# говорить для каждого маршрута (R-09 ревью).
router = APIRouter(prefix="/api", responses=E422_ALL)
SessionDep = Annotated[Session, Depends(get_session)]


def get_parser(request: Request) -> RequestParser:
    parser: RequestParser = request.app.state.parser
    return parser


def get_notifier(request: Request) -> ClientNotifier:
    notifier: ClientNotifier = request.app.state.notifier
    return notifier


ParserDep = Annotated[RequestParser, Depends(get_parser)]
NotifierDep = Annotated[ClientNotifier, Depends(get_notifier)]

E404: dict[int | str, dict[str, Any]] = {404: {"model": Problem, "description": "Не найдено"}}
E409: dict[int | str, dict[str, Any]] = {
    409: {"model": Problem, "description": "Недопустимо в текущем статусе"}
}
E422: dict[int | str, dict[str, Any]] = {
    422: {"model": Problem, "description": "Данные не проходят проверку"}
}


@router.get("/health", tags=["service"])
def health(parser: ParserDep) -> Health:
    return Health(status="ok", parser=parser.name)


@router.get("/materials", tags=["materials"])
def materials(session: SessionDep) -> list[MaterialOut]:
    return [MaterialOut.model_validate(m) for m in services.list_materials(session)]


@router.get("/requests", tags=["requests"])
def list_requests(session: SessionDep) -> list[RequestSummary]:
    return services.list_requests(session)


@router.post("/requests", status_code=201, tags=["requests"], responses=E422)
def create_request(body: RequestCreate, session: SessionDep, parser: ParserDep) -> RequestOut:
    """Создать заявку. Текст разбирается сразу: найденные поля приходят с источником
    `text` и `confirmed=false`."""
    req = services.create_request(session, parser, body.raw_text, body.fields)
    return services.request_out(req)


@router.get("/requests/{request_id}", tags=["requests"], responses=E404)
def get_request(request_id: int, session: SessionDep) -> RequestOut:
    return services.request_out(services.get_request(session, request_id))


@router.put(
    "/requests/{request_id}/fields/{key}",
    tags=["requests"],
    responses={**E404, **E409, **E422},
)
def update_field(
    request_id: int, key: FieldKey, body: FieldUpdate, session: SessionDep
) -> RequestOut:
    """Подтвердить или поправить поле. То же значение — подтверждение с сохранением
    источника; другое значение — источник `human`."""
    return services.request_out(services.update_field(session, request_id, key, body.value))


@router.post("/requests/{request_id}/transition", tags=["requests"], responses={**E404, **E409})
def transition(
    request_id: int, body: TransitionIn, session: SessionDep, notifier: NotifierDep
) -> RequestOut:
    """Перевести заявку в статус `parsed` или `sent`. Сервер проверяет условия."""
    return services.request_out(services.transition(session, notifier, request_id, body.to))


@router.put("/requests/{request_id}/design", tags=["design"], responses={**E404, **E409, **E422})
def save_design(request_id: int, body: DesignParamsIn, session: SessionDep) -> DesignOut:
    """Сохранить параметры шкафа, получить спецификацию. Статус → `designed`,
    прежняя смета удаляется."""
    return services.save_design(session, request_id, body)


@router.get("/requests/{request_id}/design", tags=["design"], responses=E404)
def get_design(request_id: int, session: SessionDep) -> DesignOut:
    return services.get_design(session, request_id)


@router.post(
    "/requests/{request_id}/estimate", tags=["estimate"], responses={**E404, **E409, **E422}
)
def calculate_estimate(request_id: int, session: SessionDep) -> EstimateOut:
    """Посчитать смету по сохранённой конструкции и текущим ценам. Статус → `estimated`."""
    return services.calculate_estimate(session, request_id)


@router.get("/requests/{request_id}/estimate", tags=["estimate"], responses=E404)
def get_estimate(request_id: int, session: SessionDep) -> EstimateOut:
    return services.get_estimate(session, request_id)
