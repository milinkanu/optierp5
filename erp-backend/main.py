import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback

from routes import auth, companies, health, invoices, onboarding, transactions
from routes.inspector import router as inspector_router

app = FastAPI()

allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
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
app.include_router(inspector_router)

if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 8000)),
        reload=True,
    )

