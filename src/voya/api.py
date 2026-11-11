"""VOYA web API (FastAPI) + the web app's static files.

Run: `uv run uvicorn voya.api:app --reload` then open http://localhost:8000
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from voya import obs
from voya.agent import HelperRequest, respond
from voya.catalog import load_catalog
from voya.discover import DiscoverRequest, discover
from voya.llm import Harness, client_from_env
from voya.planner import PlanError, PlanRequest, apply_upgrade, build, priced_for
from voya.store import Store, new_id
from voya.tracking import CATEGORIES, apply_recovery, budget_status, parse_spend_text

STATIC = Path(__file__).with_name("web")
INTERESTS = ["food", "art", "history", "architecture", "nature", "views", "nightlife", "shopping", "family"]

app = FastAPI(title="VOYA", version="0.2.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
_state: dict = {}


def store() -> Store:
    if "store" not in _state:
        _state["store"] = Store()
    return _state["store"]


def harness() -> Harness | None:
    if "harness" not in _state:
        client = client_from_env()
        _state["harness"] = Harness(client, store()) if client else None
    return _state["harness"]


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, hint: str = "") -> None:
        self.status, self.code, self.message, self.hint = status, code, message, hint


@app.exception_handler(ApiError)
async def _api_error(_: Request, e: ApiError) -> JSONResponse:
    return JSONResponse(status_code=e.status, content={"error": {
        "code": e.code, "message": e.message, "hint": e.hint, "trace_id": obs.current_trace()}})


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, e: RequestValidationError) -> JSONResponse:
    first = e.errors()[0] if e.errors() else {}
    field = ".".join(str(x) for x in first.get("loc", [])[1:]) or "input"
    return JSONResponse(status_code=422, content={"error": {
        "code": "INVALID_INPUT", "message": f"{field}: {first.get('msg', 'invalid value')}",
        "hint": "Check the highlighted field.", "trace_id": obs.current_trace()}})


@app.exception_handler(PlanError)
async def _plan_error(_: Request, e: PlanError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": {
        "code": "UNSUPPORTED", "message": str(e), "hint": "Pick one of the supported destinations.",
        "trace_id": obs.current_trace()}})


_hits: dict[str, deque] = defaultdict(deque)
RATE_PER_MIN = int(os.environ.get("VOYA_RATE_PER_MIN", "60"))


@app.middleware("http")
async def _trace_and_limit(request: Request, call_next):
    obs.new_trace()
    if request.url.path.startswith("/v1/") and request.method == "POST":
        key = request.client.host if request.client else "anon"
        q, now = _hits[key], time.monotonic()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_PER_MIN:
            return JSONResponse(status_code=429, content={"error": {
                "code": "RATE_LIMIT", "message": "Too many requests. Try again in a minute.", "hint": ""}})
        q.append(now)
    with obs.span("http", method=request.method, path=request.url.path) as sp:
        response = await call_next(request)
        sp.update(status_code=response.status_code)
    response.headers["X-Trace-Id"] = obs.current_trace() or ""
    return response


# ------------------------------------------------------------------ helpers ---


def owner(x_voya_token: str | None = Header(None)) -> str | None:
    return store().owner_for(x_voya_token)


def require_owner(o: str | None = Depends(owner)) -> str:
    if not o:
        raise ApiError(401, "SIGN_IN", "Sign in to keep this trip.", "POST /v1/auth/start")
    return o


def load_plan(plan_id: str) -> tuple[dict, PlanRequest]:
    rec = store().plan(plan_id)
    if not rec:
        raise ApiError(404, "NOT_FOUND", "That plan doesn't exist.")
    return rec, PlanRequest.model_validate_json(rec["request_json"])


def own_plan(plan_id: str, o: str) -> tuple[dict, PlanRequest]:
    rec, req = load_plan(plan_id)
    if rec["owner"] != o:
        raise ApiError(403, "NOT_YOURS", "Save this trip to your account first.")
    return rec, req


def plan_payload(plan_id: str, version: int, req: PlanRequest, owner_id: str | None) -> dict:
    with obs.span("plan.build", destination=req.destination, days=req.days):
        plan = build(req)
    return {"plan_id": plan_id, "version": version, "saved": owner_id is not None,
            "request": req.model_dump(mode="json"), "plan": plan, "trace_id": obs.current_trace()}


def new_version(plan_id: str, req: PlanRequest, reason: str, must_fit: bool = True) -> dict:
    if must_fit:
        _, _, priced = priced_for(req)
        if not priced.fit.ok:
            raise ApiError(409, "DOES_NOT_FIT", "That change would go over your budget.",
                           "Try a cheaper option or raise the budget.")
    v = store().add_version(plan_id, req.model_dump_json(), reason)
    rec = store().plan(plan_id)
    return plan_payload(plan_id, v, req, rec["owner"] if rec else None)


# -------------------------------------------------------------------- routes ---


@app.get("/v1/meta")
def meta() -> dict:
    cat = load_catalog()
    return {"destinations": [{"id": d.id, "name": d.name, "kind": d.kind} for d in cat.destinations],
            "routes": [{"from": r.from_id, "to": r.to, "drive_min": r.drive_min} for r in cat.routes],
            "interests": INTERESTS, "spend_categories": CATEGORIES,
            "demo_data": cat.synthetic, "data_notice": cat.notice if cat.synthetic else None,
            "ai_helper": "model" if harness() else "built-in"}


@app.post("/v1/plans")
def create_plan(req: PlanRequest, o: str | None = Depends(owner)) -> dict:
    pid = store().create_plan(req.model_dump_json(), owner=None)
    return plan_payload(pid, 1, req, None)


@app.get("/v1/plans/{plan_id}")
def get_plan(plan_id: str) -> dict:
    rec, req = load_plan(plan_id)
    return plan_payload(plan_id, rec["version"], req, rec["owner"])


class EditIn(BaseModel):
    gifts_amount: Decimal | None = Field(None, ge=0)
    tip_pct: Decimal | None = Field(None, ge=0, le=50)
    include_getting_there: bool | None = None
    firmness: str | None = Field(None, pattern="^(hard|wiggle)$")
    budget: Decimal | None = Field(None, gt=0)


@app.post("/v1/plans/{plan_id}/edit")
def edit_plan(plan_id: str, e: EditIn) -> dict:
    _, req = load_plan(plan_id)
    upd: dict = {}
    if e.gifts_amount is not None:
        upd["gifts_amount"] = e.gifts_amount
    if e.tip_pct is not None:
        upd["tip_pct"] = e.tip_pct
    if e.firmness:
        upd["firmness"] = e.firmness
    if e.budget is not None:
        upd["budget"] = e.budget
    if e.include_getting_there is not None:
        upd["getting_there"] = req.getting_there.model_copy(update={"include_in_total": e.include_getting_there})
    # The user's own settings are applied even if the plan stops fitting; the plan says so.
    return new_version(plan_id, req.model_copy(update=upd), "edit", must_fit=False)


@app.post("/v1/plans/{plan_id}/upgrades/{upgrade_id}")
def take_upgrade(plan_id: str, upgrade_id: str) -> dict:
    _, req = load_plan(plan_id)
    return new_version(plan_id, apply_upgrade(req, upgrade_id), f"upgrade {upgrade_id}")


@app.post("/v1/plans/{plan_id}/undo")
def undo(plan_id: str) -> dict:
    load_plan(plan_id)
    if not store().undo(plan_id):
        raise ApiError(409, "NOTHING_TO_UNDO", "This is the original plan.")
    rec, req = load_plan(plan_id)
    return plan_payload(plan_id, rec["version"], req, rec["owner"])


@app.post("/v1/discover")
def discover_route(req: DiscoverRequest) -> dict:
    with obs.span("discover", from_id=req.from_id, days=req.days):
        return discover(req)


# ------------------------------------------------------------------- accounts ---


class AuthIn(BaseModel):
    email: EmailStr
    is_adult: bool


@app.post("/v1/auth/start")
def auth_start(a: AuthIn) -> dict:
    if not a.is_adult:
        raise ApiError(403, "ADULTS_ONLY", "Accounts are for adults (18+). Trips with kids are planned from an adult's account.")
    token = store().create_user(a.email, True)
    # DEV MODE: a real deployment emails a magic link instead of returning the token.
    return {"token": token, "dev_mode": True,
            "note": "Development sign-in: in production this arrives as an email magic link."}


@app.post("/v1/plans/{plan_id}/save")
def save_plan(plan_id: str, o: str = Depends(require_owner)) -> dict:
    load_plan(plan_id)
    if not store().claim(plan_id, o):
        raise ApiError(403, "NOT_YOURS", "This trip belongs to someone else.")
    rec, req = load_plan(plan_id)
    return plan_payload(plan_id, rec["version"], req, o)


@app.get("/v1/me/trips")
def my_trips(o: str = Depends(require_owner)) -> dict:
    out = []
    for pid in store().plans_for(o):
        rec, req = load_plan(pid)
        out.append({"plan_id": pid, "destination": req.destination, "start_date": str(req.start_date),
                    "days": req.days, "budget": str(req.budget)})
    return {"trips": out}


MEMORY_KEYS = {"interests", "pace", "tip_pct", "firmness", "adults"}


class MemoryIn(BaseModel):
    values: dict[str, str] = Field(max_length=5)


@app.get("/v1/me/memory")
def memory(o: str = Depends(require_owner)) -> dict:
    return {"remembered": store().prefs(o)}


@app.post("/v1/me/memory")
def remember(m: MemoryIn, o: str = Depends(require_owner)) -> dict:
    """Only called when the user taps "Remember" (human in the loop for memory)."""
    for k, v in m.values.items():
        if k not in MEMORY_KEYS:
            raise ApiError(422, "BAD_KEY", f"VOYA doesn't remember '{k}'.", ", ".join(sorted(MEMORY_KEYS)))
        store().set_pref(o, k, v[:200], "you tapped Remember")
    return {"remembered": store().prefs(o)}


@app.delete("/v1/me/memory/{key}")
def forget(key: str, o: str = Depends(require_owner)) -> dict:
    store().forget_pref(o, key)
    return {"remembered": store().prefs(o)}


@app.get("/v1/me/export")
def export(o: str = Depends(require_owner)) -> dict:
    trips = []
    for pid in store().plans_for(o):
        rec, req = load_plan(pid)
        trips.append({"plan_id": pid, "request": req.model_dump(mode="json"), "spends": store().spends(pid)})
    return {"trips": trips, "preferences": store().prefs(o)}


@app.delete("/v1/me")
def delete_me(o: str = Depends(require_owner)) -> dict:
    store().delete_owner(o)
    return {"deleted": True}


# ---------------------------------------------------------------------- spend ---


class SpendIn(BaseModel):
    amount: Decimal | None = Field(None, gt=0, le=100_000)
    category: str | None = None
    line_id: str | None = Field(None, max_length=40)
    note: str | None = Field(None, max_length=120)
    text: str | None = Field(None, max_length=200)
    day: int | None = Field(None, ge=0, le=29)
    idempotency_key: str = Field(min_length=4, max_length=64)


@app.post("/v1/plans/{plan_id}/spend")
def add_spend(plan_id: str, s: SpendIn, o: str = Depends(require_owner)) -> dict:
    own_plan(plan_id, o)
    amount, category = s.amount, s.category
    if amount is None and s.text:
        parsed = parse_spend_text(s.text)
        if not parsed:
            raise ApiError(422, "NO_AMOUNT", "I couldn't find an amount in that.", "Try 'lunch 23.40'.")
        amount, category = parsed[0], category or parsed[1]
    if amount is None:
        raise ApiError(422, "NO_AMOUNT", "Add an amount.")
    if (category or "other") not in CATEGORIES:
        raise ApiError(422, "BAD_CATEGORY", "Unknown category.", ", ".join(CATEGORIES))
    rec, created = store().add_spend(plan_id, amount, category or "other", s.line_id, s.note or s.text, s.day, s.idempotency_key)
    _, req = load_plan(plan_id)
    return {"spend": rec, "created": created, "budget": budget_status(req, store().spends(plan_id))}


@app.get("/v1/plans/{plan_id}/budget")
def get_budget(plan_id: str, o: str = Depends(require_owner)) -> dict:
    _, req = own_plan(plan_id, o)
    spends = store().spends(plan_id)
    return {"spends": spends, "budget": budget_status(req, spends)}


@app.delete("/v1/plans/{plan_id}/spend/{spend_id}")
def delete_spend(plan_id: str, spend_id: str, o: str = Depends(require_owner)) -> dict:
    own_plan(plan_id, o)
    if not store().delete_spend(plan_id, spend_id):
        raise ApiError(404, "NOT_FOUND", "No such entry.")
    return get_budget(plan_id, o)


class RecoveryIn(BaseModel):
    slot_id: str
    action: str = Field(pattern="^(swap|skip|gifts)$")
    to_place_id: str | None = None


@app.post("/v1/plans/{plan_id}/recovery")
def take_recovery(plan_id: str, r: RecoveryIn, o: str = Depends(require_owner)) -> dict:
    _, req = own_plan(plan_id, o)
    return new_version(plan_id, apply_recovery(req, r.slot_id, r.action, r.to_place_id),
                       f"recovery {r.action} {r.slot_id}", must_fit=False)


# --------------------------------------------------------------------- helper ---


@app.post("/v1/plans/{plan_id}/helper")
def helper(plan_id: str, h: HelperRequest, request: Request, o: str | None = Depends(owner)) -> dict:
    rec, req = load_plan(plan_id)
    scope = o or (request.client.host if request.client else "anon")
    return respond(store(), plan_id, rec["version"], req, h, harness(), scope)


class ApplyIn(BaseModel):
    token: str = Field(min_length=8, max_length=64)


@app.post("/v1/plans/{plan_id}/proposals/{proposal_id}/apply")
def apply_proposal(plan_id: str, proposal_id: str, a: ApplyIn) -> dict:
    rec, _ = load_plan(plan_id)
    prop = store().take_proposal(plan_id, proposal_id, a.token)
    if not prop:
        raise ApiError(409, "PROPOSAL_USED", "That suggestion was already used or has expired.")
    if prop["base_version"] != rec["version"]:
        raise ApiError(409, "STALE", "Your plan changed since this suggestion. Ask again for fresh options.")
    new_req = PlanRequest.model_validate_json(prop["request_json"])
    return new_version(plan_id, new_req, f"proposal {proposal_id}")


# ------------------------------------------------------------------------ ops ---


@app.get("/v1/ops")
def ops(x_ops_token: str | None = Header(None)) -> dict:
    expected = os.environ.get("VOYA_OPS_TOKEN")
    if not expected or x_ops_token != expected:
        raise ApiError(401, "OPS_ONLY", "Operator token required.")
    from datetime import UTC, datetime
    now = datetime.now(UTC)
    return {"ai_spend_month_usd": str(store().ai_spent(f"month:{now:%Y-%m}")),
            "ai_helper": "model" if harness() else "built-in"}


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
