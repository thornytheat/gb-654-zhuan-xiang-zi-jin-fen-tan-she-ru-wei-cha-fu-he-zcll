from fastapi import APIRouter, Body, Request
from .service import execute
router = APIRouter(tags=["M4-金额分摊"])

@router.get("/allocations")
def page(request: Request):
    data = execute()
    return request.app.state.templates.TemplateResponse(request, "m4_allocations.html", {"title": "金额分摊", "data": data})

@router.post("/api/allocations/calculate")
def api(payload: dict = Body(default={})):
    return execute(payload or None)
