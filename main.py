import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ---- Fill these in ----
EMAIL = "22f3002678@ds.study.iitm.ac.in"
EXAM_PAGE_ORIGIN = "https://exam.sanand.workers.dev/tds-2026-09-ga2"
# -----------------------

ALLOWED_ORIGINS = [
    "https://app-9eick7.example.com",
    EXAM_PAGE_ORIGIN,
]
LIMIT = 12    # requests allowed
WINDOW = 10   # seconds

app = FastAPI()
hits = defaultdict(deque)  # client_id -> timestamps of recent requests


# Desk 2: rate limiter (added first = innermost)
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.method == "OPTIONS":          # don't count preflight checks
        return await call_next(request)

    client_id = request.headers.get("X-Client-Id") or (
        request.client.host if request.client else "anonymous"
    )
    now = time.monotonic()
    q = hits[client_id]

    while q and now - q[0] >= WINDOW:        # forget visits older than 10s
        q.popleft()

    if len(q) >= LIMIT:
        return JSONResponse({"detail": "Too many requests"}, status_code=429)

    q.append(now)
    return await call_next(request)


# Desk 1: request context (added second = middle)
@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# Desk 3: CORS (added last = outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,           # exact list, no "*"
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type"],
    expose_headers=["X-Request-ID"],
)


@app.get("/ping")
async def ping(request: Request):
    return {"email": EMAIL, "request_id": request.state.request_id}