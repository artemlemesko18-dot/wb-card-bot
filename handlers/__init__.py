from .admin import router as admin_router
from .balance import router as balance_router
from .generation import router as generation_router
from .payments import router as payments_router
from .start import router as start_router

__all__ = [
    "start_router",
    "generation_router",
    "balance_router",
    "payments_router",
    "admin_router",
]
