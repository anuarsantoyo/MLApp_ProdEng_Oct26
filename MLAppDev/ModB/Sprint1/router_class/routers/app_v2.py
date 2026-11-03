# uvicorn MLAppDev.ModB.Sprint1.router_class.routers.app_v2:app --reload --port 8011     (run from this folder)
#
# The "after". No routes in here, just the wiring.
from fastapi import FastAPI

# Same shape as `from shop import greet` in part 1: the package gives you the file,
# and the file gives you the router.
from .route import health, items

app = FastAPI(title="routers demo")

# Two places to put a prefix, same result. Pick one and stay there.

# 1. Here, when you plug the router in. items.py has no "/items" anywhere.
app.include_router(items.router, prefix="/items", tags=["items"])

# 2. In the router file itself. health.py already says prefix="/health",
#    so there is nothing to add here.
app.include_router(health.router)


