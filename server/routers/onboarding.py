from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User, UserProfile
from routers.auth import get_current_user
from schemas.onboarding import OnboardingRequest, OnboardingResponse


router = APIRouter(
    prefix="/onboarding",
    tags=["Onboarding"]
)


@router.post("/complete", response_model=OnboardingResponse)
def complete_onboarding(
    request: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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