from fastapi import APIRouter, Body, Request
from .service import execute
router = APIRouter(tags=["M3-权重测算"])

@router.get("/weights")
def page(request: Request):
    data = execute()
    return request.app.state.templates.TemplateResponse(request, "m3_weights.html", {"title": "权重测算", "data": data})

@router.post("/api/weights/calculate")
def api(payload: dict = Body(default={})):
    return execute(payload or None)
