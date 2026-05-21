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
from routes.inspector import router as inspector_router

app = FastAPI()

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

from fastapi.exceptions import HTTPException as FastAPIHTTPException, RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    if isinstance(exc, (FastAPIHTTPException, StarletteHTTPException)):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body": exc.body},
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
app.include_router(inspector_router)

if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 8000)),
        reload=True,
    )

