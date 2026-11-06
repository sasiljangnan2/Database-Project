"""예정 API 계약의 요청·응답 모델. 이 파일을 구현과 함께 갱신한다."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel, PatchModel


class Station(APIModel):
    id: int = Field(ge=1, strict=True)
    name: str = Field(min_length=1)
    region: str | None = Field(max_length=100, description="ERD 밖의 선택 정보")
    is_active: bool = Field(strict=True)


class StationCreate(APIModel):
    name: str = Field(min_length=1)
    region: str | None = Field(default=None, max_length=100, description="ERD 밖의 선택 정보")
    is_active: bool = Field(strict=True)


class StationPatch(PatchModel):
    name: str = Field(default=None, min_length=1)
    region: str | None = Field(default=None, max_length=100, description="ERD 밖의 선택 정보")
    is_active: bool = Field(default=None, strict=True)


class Train(APIModel):
    id: int = Field(ge=1, strict=True)
    identifier: str = Field(min_length=1)
    train_type_code: str = Field(min_length=1, max_length=30, description="train_types.code 참조")
    is_active: bool = Field(strict=True)


class TrainCreate(APIModel):
    identifier: str = Field(min_length=1)
    train_type_code: str = Field(min_length=1, max_length=30, description="train_types.code 참조")
    is_active: bool = Field(strict=True)


class TrainPatch(PatchModel):
    identifier: str = Field(default=None, min_length=1)
    train_type_code: str = Field(
        default=None, min_length=1, max_length=30, description="train_types.code 참조"
    )
    is_active: bool = Field(default=None, strict=True)


class Seat(APIModel):
    id: int = Field(ge=1, strict=True)
    train_id: int = Field(ge=1, strict=True)
    carriage_no: int = Field(ge=1, strict=True)
    seat_number: str = Field(min_length=1)
    seat_class: str = Field(min_length=1)


class SeatCreate(APIModel):
    train_id: int = Field(ge=1, strict=True)
    carriage_no: int = Field(ge=1, strict=True)
    seat_number: str = Field(min_length=1)
    seat_class: str = Field(min_length=1)


class SeatPatch(PatchModel):
    train_id: int = Field(default=None, ge=1, strict=True)
    carriage_no: int = Field(default=None, ge=1, strict=True)
    seat_number: str = Field(default=None, min_length=1)
    seat_class: str = Field(default=None, min_length=1)


class Route(APIModel):
    id: int = Field(ge=1, strict=True)
    name: str = Field(min_length=1)
    is_active: bool = Field(strict=True)


class RouteCreate(APIModel):
    name: str = Field(min_length=1)
    is_active: bool = Field(strict=True)


class RoutePatch(PatchModel):
    name: str = Field(default=None, min_length=1)
    is_active: bool = Field(default=None, strict=True)


class RouteStop(APIModel):
    id: int = Field(ge=1, strict=True)
    route_id: int = Field(ge=1, strict=True)
    station_id: int = Field(ge=1, strict=True)
    stop_order: int = Field(ge=1, strict=True)


class RouteStopCreate(APIModel):
    route_id: int = Field(ge=1, strict=True)
    station_id: int = Field(ge=1, strict=True)
    stop_order: int = Field(ge=1, strict=True)


class RouteStopPatch(PatchModel):
    route_id: int = Field(default=None, ge=1, strict=True)
    station_id: int = Field(default=None, ge=1, strict=True)
    stop_order: int = Field(default=None, ge=1, strict=True)


class Run(APIModel):
    id: int = Field(ge=1, strict=True)
    train_id: int = Field(ge=1, strict=True)
    route_id: int = Field(ge=1, strict=True)
    service_number: str = Field(min_length=1)
    service_date: date
    status: Literal["ON_SALE", "CLOSED", "CANCELLED"]
    direction: str = Field(min_length=1, max_length=50)


class RunCreate(APIModel):
    train_id: int = Field(ge=1, strict=True)
    route_id: int = Field(ge=1, strict=True)
    service_number: str = Field(min_length=1)
    service_date: date
    status: Literal["ON_SALE", "CLOSED"]
    direction: str = Field(min_length=1, max_length=50)


class RunPatch(PatchModel):
    train_id: int = Field(default=None, ge=1, strict=True)
    route_id: int = Field(default=None, ge=1, strict=True)
    service_number: str = Field(default=None, min_length=1)
    service_date: date = Field(default=None)
    status: Literal["ON_SALE", "CLOSED"] = Field(default=None)
    direction: str = Field(default=None, min_length=1, max_length=50)


class RunStop(APIModel):
    id: int = Field(ge=1, strict=True)
    run_id: int = Field(ge=1, strict=True)
    route_stop_id: int = Field(ge=1, strict=True)
    stop_order: int = Field(ge=1, strict=True)
    arrival_at: datetime | None
    departure_at: datetime | None


class RunStopCreate(APIModel):
    run_id: int = Field(ge=1, strict=True)
    route_stop_id: int = Field(ge=1, strict=True)
    stop_order: int = Field(ge=1, strict=True)
    arrival_at: datetime | None
    departure_at: datetime | None


class RunStopPatch(PatchModel):
    run_id: int = Field(default=None, ge=1, strict=True)
    route_stop_id: int = Field(default=None, ge=1, strict=True)
    stop_order: int = Field(default=None, ge=1, strict=True)
    arrival_at: datetime | None = Field(default=None)
    departure_at: datetime | None = Field(default=None)


class Fare(APIModel):
    id: int = Field(ge=1, strict=True)
    departure_station_id: int = Field(ge=1, strict=True)
    arrival_station_id: int = Field(ge=1, strict=True)
    train_type_code: str = Field(min_length=1, max_length=30, description="train_types.code 참조")
    seat_class: str = Field(min_length=1)
    amount: int = Field(ge=0, description="KRW 정수", strict=True)


class FareCreate(APIModel):
    departure_station_id: int = Field(ge=1, strict=True)
    arrival_station_id: int = Field(ge=1, strict=True)
    train_type_code: str = Field(min_length=1, max_length=30, description="train_types.code 참조")
    seat_class: str = Field(min_length=1)
    amount: int = Field(ge=0, description="KRW 정수", strict=True)


class FarePatch(PatchModel):
    departure_station_id: int = Field(default=None, ge=1, strict=True)
    arrival_station_id: int = Field(default=None, ge=1, strict=True)
    train_type_code: str = Field(
        default=None, min_length=1, max_length=30, description="train_types.code 참조"
    )
    seat_class: str = Field(default=None, min_length=1)
    amount: int = Field(default=None, ge=0, description="KRW 정수", strict=True)


class FareSummary(APIModel):
    seat_class: str = Field(min_length=1)
    amount: int = Field(ge=0, description="KRW 정수", strict=True)
    available_seats: int = Field(ge=0, strict=True)


class RunSearchItem(APIModel):
    run_id: int = Field(ge=1, strict=True)
    service_number: str = Field(min_length=1)
    train_type_code: str = Field(min_length=1, max_length=30, description="train_types.code 참조")
    boarding_run_stop_id: int = Field(ge=1, strict=True)
    alighting_run_stop_id: int = Field(ge=1, strict=True)
    departure_at: datetime
    arrival_at: datetime
    fares: list[FareSummary]
    train_type_name: str = Field(min_length=1, max_length=100)
    direction: str = Field(min_length=1, max_length=50)


class SeatAvailability(APIModel):
    seat_id: int = Field(ge=1, strict=True)
    carriage_no: int = Field(ge=1, strict=True)
    seat_number: str = Field(min_length=1)
    seat_class: str = Field(min_length=1)
    available: bool = Field(strict=True)
    amount: int = Field(ge=0, description="KRW 정수", strict=True)


class TrainType(APIModel):
    code: str = Field(min_length=1, max_length=30, description="열차종류 기본키")
    name: str = Field(min_length=1, max_length=100)


class TrainTypeCreate(APIModel):
    code: str = Field(
        min_length=1, max_length=30, description="생성 후 변경하지 않는 열차종류 기본키"
    )
    name: str = Field(min_length=1, max_length=100)


class TrainTypePatch(PatchModel):
    name: str = Field(default=None, min_length=1, max_length=100)
