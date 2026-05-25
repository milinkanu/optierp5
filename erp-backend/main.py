import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback

from routes import auth, companies, health, invoices, onboarding, transactions, quotes, sales_orders
from routes import chart_of_accounts, contacts, items
from routes import recurring_invoices, delivery_challans, payments, credit_notes
from routes.inspector import router as inspector_router
from services.scheduler import start_scheduler, stop_scheduler

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()

dev_allow_all = os.getenv("DEV_ALLOW_ALL_ORIGINS", "true").lower() == "true"
allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:5173"]

allow_origin_regex = os.getenv("ALLOW_ORIGIN_REGEX", r"^https?://localhost(:\d+)?$")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if dev_allow_all else allowed_origins,
    allow_origin_regex=None if dev_allow_all else allow_origin_regex,
    allow_credentials=False if dev_allow_all else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_cors_headers(request) -> dict[str, str]:
    origin = request.headers.get("origin")
    if not origin:
        return {}
    
    headers = {}
    is_allowed = False
    
    if dev_allow_all:
        is_allowed = True
    else:
        if origin in allowed_origins:
            is_allowed = True
        elif allow_origin_regex:
            import re
            try:
                if re.match(allow_origin_regex, origin):
                    is_allowed = True
            except Exception:
                pass
                
    if is_allowed:
        headers["Access-Control-Allow-Origin"] = origin
        if not dev_allow_all:
            headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "*"
        headers["Access-Control-Allow-Headers"] = "*"
        headers["Access-Control-Expose-Headers"] = "*"
        
    return headers

from fastapi.exceptions import HTTPException as FastAPIHTTPException, RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    cors_headers = get_cors_headers(request)
    if isinstance(exc, (FastAPIHTTPException, StarletteHTTPException)):
        resp_headers = dict(getattr(exc, "headers", None) or {})
        resp_headers.update(cors_headers)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=resp_headers,
        )
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body": exc.body},
            headers=cors_headers,
        )
    # Ensure we return JSON (and still pass through CORS middleware) during dev.
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc().splitlines(),
        },
        headers=cors_headers,
    )

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(onboarding.router)
app.include_router(invoices.router)
app.include_router(transactions.router)
app.include_router(chart_of_accounts.router)
app.include_router(contacts.router)
app.include_router(items.router)
app.include_router(quotes.router)
app.include_router(sales_orders.router)
app.include_router(recurring_invoices.router)
app.include_router(delivery_challans.router)
app.include_router(payments.router)
app.include_router(credit_notes.router)
app.include_router(inspector_router)

if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 8000)),
        reload=True,
    )

