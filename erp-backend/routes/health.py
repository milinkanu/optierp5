from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/")
async def root():
    return {
        "name": "OptiERP API",
        "status": "ok",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health",
    }

