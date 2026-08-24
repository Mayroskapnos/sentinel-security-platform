from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.asset import AssetCreate, AssetFilters, AssetResponse, AssetUpdate
from app.schemas.common import Page
from app.services.assets import AssetService

router = APIRouter(prefix="/assets", tags=["assets"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=Page[AssetResponse], summary="List and filter assets")
async def list_assets(
    session: SessionDependency,
    filters: Annotated[AssetFilters, Query()],
) -> Page[AssetResponse]:
    return await AssetService(session).list(filters)


@router.get("/{asset_id}", response_model=AssetResponse, summary="Get an asset")
async def get_asset(asset_id: UUID, session: SessionDependency) -> AssetResponse:
    return await AssetService(session).get(asset_id)


@router.post(
    "",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an asset",
)
async def create_asset(payload: AssetCreate, session: SessionDependency) -> AssetResponse:
    return await AssetService(session).create(payload)


@router.patch("/{asset_id}", response_model=AssetResponse, summary="Update an asset")
async def update_asset(
    asset_id: UUID, payload: AssetUpdate, session: SessionDependency
) -> AssetResponse:
    return await AssetService(session).update(asset_id, payload)
