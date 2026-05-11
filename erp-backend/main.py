import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import auth, companies, health, invoices, onboarding, transactions
from routes.inspector import router as inspector_router

app = FastAPI()

allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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

