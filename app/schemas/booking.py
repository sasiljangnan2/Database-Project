"""예정 API 계약의 요청·응답 모델. 이 파일을 구현과 함께 갱신한다."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel


class ReservationCreate(APIModel):
    run_id: int = Field(ge=1, strict=True)
    boarding_run_stop_id: int = Field(ge=1, strict=True)
    alighting_run_stop_id: int = Field(ge=1, strict=True)
    passenger_count: int = Field(ge=1, le=9, strict=True)
    seat_ids: list[int] = Field(min_length=1, max_length=9)

    @model_validator(mode="after")
    def validate_selection(self):
        if len(self.seat_ids) != len(set(self.seat_ids)):
            raise ValueError("중복 좌석은 선택할 수 없습니다.")
        if len(self.seat_ids) != self.passenger_count:
            raise ValueError("인원수와 선택 좌석수가 같아야 합니다.")
        if self.boarding_run_stop_id == self.alighting_run_stop_id:
            raise ValueError("승차와 하차 지점은 달라야 합니다.")
        return self


class Ticket(APIModel):
    id: int = Field(ge=1, strict=True)
    reservation_id: int = Field(ge=1, strict=True)
    seat_id: int = Field(ge=1, strict=True)
    boarding_run_stop_id: int = Field(ge=1, strict=True)
    alighting_run_stop_id: int = Field(ge=1, strict=True)
    fare_id: int = Field(ge=1, strict=True)
    confirmed_amount: int = Field(ge=0, description="KRW 정수", strict=True)
    status: Literal["HELD", "ISSUED", "BOARDED", "CANCELLED", "EXPIRED"]
    issued_at: datetime | None
    cancelled_at: datetime | None


class Payment(APIModel):
    id: int = Field(ge=1, strict=True)
    reservation_id: int = Field(ge=1, strict=True)
    amount: int = Field(ge=0, description="KRW 정수", strict=True)
    method: Literal["DEMO_CARD", "DEMO_TRANSFER"]
    status: Literal["SUCCEEDED", "FAILED"]
    created_at: datetime


class Refund(APIModel):
    id: int = Field(ge=1, strict=True)
    payment_id: int = Field(ge=1, strict=True)
    ticket_id: int = Field(ge=1, strict=True)
    amount: int = Field(ge=0, description="KRW 정수", strict=True)
    reason: Literal["USER_CANCELLED", "RUN_CANCELLED"]
    status: Literal["PENDING", "SUCCEEDED", "FAILED"]
    created_at: datetime
    processed_at: datetime | None


class ReservationSummary(APIModel):
    id: int = Field(ge=1, strict=True)
    run_id: int = Field(ge=1, strict=True)
    status: Literal["PENDING_PAYMENT", "PAID", "PARTIALLY_CANCELLED", "CANCELLED", "EXPIRED"]
    created_at: datetime
    expires_at: datetime
    total_amount: int = Field(ge=0, description="KRW 정수", strict=True)


class Reservation(APIModel):
    id: int = Field(ge=1, strict=True)
    run_id: int = Field(ge=1, strict=True)
    status: Literal["PENDING_PAYMENT", "PAID", "PARTIALLY_CANCELLED", "CANCELLED", "EXPIRED"]
    created_at: datetime
    expires_at: datetime
    total_amount: int = Field(ge=0, description="KRW 정수", strict=True)
    tickets: list[Ticket]
    payments: list[Payment]
    refunds: list[Refund]


class PaymentCreate(APIModel):
    method: Literal["DEMO_CARD", "DEMO_TRANSFER"]
    demo_result: Literal["SUCCESS", "FAILURE"]


class TicketCancel(APIModel):
    ticket_ids: list[int] = Field(min_length=1)

    @field_validator("ticket_ids")
    @classmethod
    def unique_tickets(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("승차권 ID가 중복되었습니다.")
        return value


class Cancellation(APIModel):
    reservation: Reservation
    refunds: list[Refund]


class RunCancelResult(APIModel):
    run_id: int = Field(ge=1, strict=True)
    status: Literal["CANCELLED"]
    cancelled_reservations: int = Field(ge=0, strict=True)
    pending_refunds: int = Field(ge=0, strict=True)


class Boarding(APIModel):
    id: int = Field(ge=1, strict=True)
    ticket_id: int = Field(ge=1, strict=True)
    checked_by: int = Field(ge=1, strict=True)
    checked_at: datetime


class RefundProcess(APIModel):
    demo_result: Literal["SUCCESS", "FAILURE"]
