from fastapi import APIRouter

from app.api.endpoints import (
    admin_catalog,
    admin_operations,
    auth,
    catalog,
    refunds,
    reservations,
    runs,
    system,
    tickets,
    users,
)

api_router = APIRouter()
for domain in (
    system,
    auth,
    users,
    catalog,
    runs,
    reservations,
    tickets,
    refunds,
    admin_catalog,
    admin_operations,
):
    api_router.include_router(domain.router)
