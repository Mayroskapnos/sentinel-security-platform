from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.asset import Asset
from app.repositories.assets import AssetRepository
from app.schemas.asset import AssetCreate, AssetFilters, AssetResponse, AssetUpdate
from app.schemas.common import Page


class AssetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AssetRepository(session)

    async def list(self, filters: AssetFilters) -> Page[AssetResponse]:
        assets, total = await self.repository.list(filters)
        return Page[AssetResponse].create(
            items=[AssetResponse.model_validate(asset) for asset in assets],
            page=filters.page,
            page_size=filters.page_size,
            total=total,
        )

    async def get(self, asset_id: UUID) -> AssetResponse:
        asset = await self.repository.get(asset_id)
        if asset is None:
            raise NotFoundError("ASSET_NOT_FOUND", "Requested asset does not exist.")
        return AssetResponse.model_validate(asset)

    async def create(self, payload: AssetCreate) -> AssetResponse:
        asset = Asset(**payload.model_dump())
        try:
            await self.repository.create(asset)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "ASSET_ALREADY_EXISTS", "An asset with this hostname or IP address already exists."
            ) from exc
        return AssetResponse.model_validate(asset)

    async def update(self, asset_id: UUID, payload: AssetUpdate) -> AssetResponse:
        asset = await self.repository.get(asset_id)
        if asset is None:
            raise NotFoundError("ASSET_NOT_FOUND", "Requested asset does not exist.")

        changes = payload.model_dump(exclude_unset=True)
        first_seen = changes.get("first_seen", asset.first_seen)
        last_seen = changes.get("last_seen", asset.last_seen)
        if last_seen < first_seen:
            raise ConflictError("INVALID_ASSET_TIMELINE", "last_seen cannot precede first_seen.")
        for field, value in changes.items():
            setattr(asset, field, value)

        try:
            await self.session.commit()
            await self.session.refresh(asset)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "ASSET_ALREADY_EXISTS", "An asset with this IP address already exists."
            ) from exc
        return AssetResponse.model_validate(asset)
