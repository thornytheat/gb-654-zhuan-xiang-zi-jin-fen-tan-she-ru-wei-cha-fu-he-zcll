from fastapi import APIRouter, Body, Request
from .service import execute
router = APIRouter(tags=["M1-预算采信"])

@router.get("/budgets")
def page(request: Request):
    data = execute()
    return request.app.state.templates.TemplateResponse(request, "m1_budgets.html", {"title": "预算采信", "data": data})

@router.post("/api/budgets/import")
def api(payload: dict = Body(default={})):
    return execute(payload or None)
