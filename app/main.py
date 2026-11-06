from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import register_error_handlers

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, version="0.2.0")
    register_error_handlers(application)
    application.include_router(api_router, prefix="/api/v1")
    application.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    preview_enabled = settings.enable_frontend_preview

    @application.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home(request: Request):
        return templates.TemplateResponse(
            request=request, name="index.html", context={"preview_enabled": preview_enabled}
        )

    if preview_enabled:

        @application.get("/dev/preview", response_class=HTMLResponse, include_in_schema=False)
        def frontend_preview(request: Request):
            return templates.TemplateResponse(
                request=request, name="preview.html", context={"preview_enabled": True}
            )

    return application


app = create_app()
