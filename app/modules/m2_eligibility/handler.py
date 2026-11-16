from fastapi import APIRouter, Body, Request
from .service import execute
router = APIRouter(tags=["M2-资格校验"])

@router.get("/eligibility")
def page(request: Request):
    data = execute()
    return request.app.state.templates.TemplateResponse(request, "m2_eligibility.html", {"title": "资格校验", "data": data})

@router.post("/api/eligibility/evaluate")
def api(payload: dict = Body(default={})):
    return execute(payload or None)
