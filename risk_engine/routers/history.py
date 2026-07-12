from fastapi import APIRouter
from database import get_all_history

router = APIRouter()


@router.get("/history")
def get_history():
    return {"history": get_all_history()}