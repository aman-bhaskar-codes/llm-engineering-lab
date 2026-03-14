from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Structured Extraction Engine Running"}