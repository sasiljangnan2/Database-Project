"""김용우: 역·열차종류 공개 조회."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import DbSession
from app.schemas.catalog import Station, TrainType
from app.schemas.common import Error, Page
from app.services import catalog

router = APIRouter(
    prefix="", tags=["catalog"], responses={code: {"model": Error} for code in (422, 503)}
)

PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Keyword = Annotated[str | None, Query(max_length=100)]


@router.get("/stations", response_model=Page[Station], operation_id="get__stations")
def list_stations(
    db: DbSession, page: PageNumber = 1, size: PageSize = 20, keyword: Keyword = None
):
    """운영 중인 역만 id 오름차순으로 조회한다. 인증 없이 사용할 수 있다."""
    return catalog.public_stations(db, page, size, keyword)


@router.get("/train-types", response_model=Page[TrainType], operation_id="list_train_types")
def list_train_types(
    db: DbSession, page: PageNumber = 1, size: PageSize = 20, keyword: Keyword = None
):
    """열차종류 코드와 종류명을 code 오름차순으로 조회한다."""
    return catalog.public_train_types(db, page, size, keyword)
