from fastapi import APIRouter
from app.api.endpoints.recommendation import router as recommendation_router
from app.api.endpoints.library import router as library_router
from app.api.endpoints.proxy import router as proxy_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.search import router as search_router

api_router = APIRouter()

# Mount authentication endpoints at /auth
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

# Mount search endpoints at /search
api_router.include_router(
    search_router,
    prefix="/search",
    tags=["Live Search"],
)

# Mount recommendation endpoints at /recommend
api_router.include_router(
    recommendation_router,
    prefix="/recommend",
    tags=["AI Recommendations"],
)

# Mount user library endpoints at /library
api_router.include_router(
    library_router,
    prefix="/library",
    tags=["User Library"],
)

# Mount image proxy endpoints at /proxy
api_router.include_router(
    proxy_router,
    prefix="/proxy",
    tags=["Image Proxy"],
)


