from fastapi import APIRouter, Body, Request
from .service import execute
router = APIRouter(tags=["M5-尾差裁决"])

@router.get("/remainders")
def page(request: Request):
    data = execute()
    return request.app.state.templates.TemplateResponse(request, "m5_remainders.html", {"title": "尾差裁决", "data": data})

@router.post("/api/remainders/resolve")
def api(payload: dict = Body(default={})):
    return execute(payload or None)
