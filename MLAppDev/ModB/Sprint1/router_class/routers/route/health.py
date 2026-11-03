from fastapi import APIRouter

# This router carries its own prefix and tag, so main.py plugs it in with no arguments.
# The route below stays "/" and still answers on /health/.
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
def health():
    return {"status": "ok"}
