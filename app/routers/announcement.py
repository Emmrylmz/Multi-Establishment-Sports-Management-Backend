from fastapi import APIRouter, Depends, Request, status
from .BaseRouter import BaseRouter, get_base_router

router = APIRouter()


@router.post("/private_course_requests", response_model=PrivateCourseRequestOut)
async def create_private_course_request(request: PrivateCourseRequestCreate):
    
