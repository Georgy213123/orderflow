from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.domain.parser import build_parser
from app.integrations.notifier import LogNotifier
from app.services import DomainError

API_VERSION = "0.3.1"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="OrderFlow API",
        version=API_VERSION,
        description="Мастерская корпусной мебели: заявка → конструкция изделия → смета. "
        "Демо, данные вымышленные.",
    )
    app.state.parser = build_parser(
        settings.request_parser, settings.llm_api_url, settings.llm_api_key
    )
    app.state.notifier = LogNotifier()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def _problem(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.message, "problems": exc.problems},
        )

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
        problems = [
            f"{'.'.join(str(x) for x in err['loc'][1:])}: {err['msg']}" for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422, content={"message": "неверный запрос", "problems": problems}
        )

    app.include_router(router)
    return app


app = create_app()
