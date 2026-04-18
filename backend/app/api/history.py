"""
History endpoints — user prediction history and single-prediction detail.

GET /history
GET /prediction/{prediction_id}
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.models.user import User
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.upload_repository import UploadRepository
from app.schemas.prediction import HistoryItem, HistoryResponse, PredictionSchema
from app.schemas.response import APIResponse

router = APIRouter(tags=["History"])


@router.get(
    "/history",
    response_model=APIResponse[HistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List all predictions made by the current user",
)
async def get_history(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[HistoryResponse]:
    upload_repo = UploadRepository(db)
    uploads, total = await upload_repo.get_user_uploads(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    items: list[HistoryItem] = []
    for upload in uploads:
        pred = upload.prediction
        items.append(
            HistoryItem(
                upload_id=upload.id,
                prediction_id=pred.id if pred else None,
                image_url=upload.image_url,
                plant_name=pred.plant_name if pred else None,
                disease_name=pred.disease_name if pred else None,
                confidence_score=pred.confidence_score if pred else None,
                is_plant=pred.is_plant if pred else False,
                fallback_used=pred.fallback_used if pred else False,
                uploaded_at=upload.uploaded_at,
                created_at=pred.created_at if pred else None,
            )
        )

    has_next = (page * page_size) < total

    return APIResponse.ok(
        HistoryResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
        ),
        f"Found {total} record(s)",
    )


@router.get(
    "/prediction/{prediction_id}",
    response_model=APIResponse[PredictionSchema],
    status_code=status.HTTP_200_OK,
    summary="Retrieve a single prediction by ID",
)
async def get_prediction(
    prediction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[PredictionSchema]:
    prediction_repo = PredictionRepository(db)
    prediction = await prediction_repo.get_by_id(prediction_id)

    if prediction is None:
        raise ResourceNotFoundError(
            f"Prediction '{prediction_id}' not found"
        )

    # Security: ensure the prediction belongs to the requesting user
    upload_repo = UploadRepository(db)
    upload = await upload_repo.get_by_id(prediction.upload_id)

    if upload is None or upload.user_id != current_user.id:
        raise PermissionDeniedError(
            "You do not have access to this prediction"
        )

    return APIResponse.ok(
        PredictionSchema.model_validate(prediction),
        "Prediction retrieved successfully",
    )
