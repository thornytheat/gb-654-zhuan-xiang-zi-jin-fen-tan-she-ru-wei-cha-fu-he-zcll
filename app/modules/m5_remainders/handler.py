import json
from fastapi import APIRouter, Body, Request
from . import service
from .core import SETTLE_SAMPLE

router = APIRouter(tags=["M5-尾差裁决"])


@router.get("/remainders")
def page(request: Request):
    store = request.app.state.store
    recovered = service.recover(store)  # 打开页面即恢复中断的未完裁决
    data = service.execute()
    return request.app.state.templates.TemplateResponse(request, "m5_remainders.html", {
        "title": "尾差裁决", "data": data,
        "settle_sample": {"pool_id": SETTLE_SAMPLE["pool_id"], "total": SETTLE_SAMPLE["total"],
                          "items_json": json.dumps(SETTLE_SAMPLE["items"], ensure_ascii=False, indent=2)},
        "pools": service.pools_view(store),
        "ledger": service.ledger_view(store),
        "batches": service.batches_view(store),
        "recovered": recovered,
    })


@router.post("/api/remainders/resolve")
def api(payload: dict = Body(default={})):
    return service.execute(payload or None)


@router.post("/api/remainders/settle")
def settle(request: Request, payload: dict = Body(default={})):
    return service.settle(request.app.state.store, payload or None)


@router.get("/api/remainders/ledger")
def ledger(request: Request, pool_id: str | None = None):
    store = request.app.state.store
    return {"pools": service.pools_view(store), "ledger": service.ledger_view(store, pool_id)}


@router.get("/api/remainders/batches")
def batches(request: Request, pool_id: str | None = None):
    return {"batches": service.batches_view(request.app.state.store, pool_id)}


@router.get("/api/remainders/batches/{batch_id}")
def batch(request: Request, batch_id: str):
    return service.batch_view(request.app.state.store, batch_id)


@router.post("/api/remainders/batches/{batch_id}/verify")
def verify(request: Request, batch_id: str):
    return service.verify(request.app.state.store, batch_id)


@router.post("/api/remainders/recover")
def recover(request: Request):
    return {"recovered": service.recover(request.app.state.store)}
