from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User, UserProfile
from routers.auth import get_current_user
from schemas.onboarding import OnboardingRequest, OnboardingResponse
from services.career_benchmarks import career_benchmarks


router = APIRouter(
    prefix="/onboarding",
    tags=["Onboarding"]
)


@router.get("/me", response_model=OnboardingResponse)
def get_onboarding_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding profile not found"
        )
    return profile


@router.post("/complete", response_model=OnboardingResponse)
def complete_onboarding(
    request: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not career_benchmarks.get_role(request.career_goal):
        supported = ", ".join(role["title"] for role in career_benchmarks.supported_roles())
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported career path. Choose one of: {supported}.",
        )
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )

    if profile is None:
        profile = UserProfile(
            user_id=current_user.id
        )
        db.add(profile)

    profile.subject = request.subject
    profile.career_goal = request.career_goal
    profile.time_commitment_hrs = request.time_commitment_hrs
    profile.primary_language = request.primary_language.value
    profile.secondary_language = (
        request.secondary_language.value
        if request.secondary_language
        else None
    )
    profile.perceived_level = request.perceived_level.value

    profile.prior_exposure = request.prior_exposure

    profile.preferred_question_types = (
        [q.value for q in request.preferred_question_types]
        if request.preferred_question_types
        else None
    )

    db.commit()
    db.refresh(profile)

    return profile
