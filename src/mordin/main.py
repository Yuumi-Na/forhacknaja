"""FastAPI app for the local demo page: start, chat and the static page. Thai bubbles only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from mordin.explain import messages
from mordin.flows import Text
from mordin.flows.session import State
from mordin.flows.types import Button, ButtonSpec, ImageUploaded, Reply
from mordin.service import Service

MAX_UPLOAD_BYTES = 10_485_760  # 10 MB (requirement 1.3, 1.6)
STATIC_INDEX = Path(__file__).parent / "web" / "static" / "index.html"
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_service: Service | None = None


def get_service() -> Service:
    """One Service per process, created on first use so imports need no data or AWS."""
    global _service
    if _service is None:
        _service = Service()
    return _service


def _is_image(data: bytes) -> bool:
    return data.startswith(_JPEG_MAGIC) or data.startswith(_PNG_MAGIC)


def _upload_problem(key: str, session_id: str, state: str) -> dict[str, Any]:
    """A Thai bubble that keeps the upload button. No session is created or changed."""
    spec = Reply(key, buttons=[ButtonSpec("button.upload_sheet", "upload_sheet")])
    return {"session_id": session_id, "state": state, "bubbles": [messages.render(spec)]}


def _current_state(service: Service, session_id: str) -> str:
    try:
        return service.store.get(session_id).state.value
    except Exception:
        return State.FAILED.value


def _generic_error(session_id: str) -> dict[str, Any]:
    spec = Reply("error.generic", buttons=[ButtonSpec("button.restart", "restart")])
    return {"session_id": session_id, "state": State.FAILED.value, "bubbles": [messages.render(spec)]}


def create_app(service: Service | None = None) -> FastAPI:
    app = FastAPI(title="Mor Din AI", docs_url=None, redoc_url=None, openapi_url=None)

    def svc() -> Service:
        return service if service is not None else get_service()

    @app.get("/")
    def index() -> Any:
        if not STATIC_INDEX.is_file():
            return JSONResponse({"detail": "page not built"}, status_code=404)
        return FileResponse(STATIC_INDEX, media_type="text/html; charset=utf-8")

    @app.post("/api/start")
    def start() -> dict[str, Any]:
        body = svc().start()
        body["stub"] = bool(svc().stub)  # the page shows the sample-data badge
        return body

    @app.post("/api/chat")
    def chat(
        session_id: str = Form(...),
        text: str | None = Form(None),
        action: str | None = Form(None),
        payload: str | None = Form(None),
        image: UploadFile | None = File(None),
    ) -> dict[str, Any]:
        if image is not None and image.filename:
            data = image.file.read(MAX_UPLOAD_BYTES + 1)
            if len(data) > MAX_UPLOAD_BYTES:
                state = _current_state(svc(), session_id)
                return _upload_problem("upload.too_large", session_id, state)
            if not data or not _is_image(data):
                state = _current_state(svc(), session_id)
                return _upload_problem("upload.ask", session_id, state)
            return svc().handle(session_id, ImageUploaded(filename=image.filename), image=data)
        if action:
            return svc().handle(session_id, Button(action=action, payload=payload))
        if text is not None:
            return svc().handle(session_id, Text(text=text))
        return _generic_error(session_id)

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
