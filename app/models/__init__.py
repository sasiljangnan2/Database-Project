"""16개 모델을 등록한다. DB 생성·변경은 수행하지 않는다."""

from app.models.boarding_check import BoardingCheck
from app.models.fare import Fare
from app.models.payment import Payment
from app.models.refund import Refund
from app.models.reservation import Reservation
from app.models.route import Route
from app.models.route_stop import RouteStop
from app.models.run import Run
from app.models.run_stop import RunStop
from app.models.seat import Seat
from app.models.seat_occupancy import SeatOccupancy
from app.models.station import Station
from app.models.ticket import Ticket
from app.models.train import Train
from app.models.train_type import TrainType
from app.models.user import User

__all__ = [
    "User",
    "Station",
    "TrainType",
    "Train",
    "Seat",
    "Route",
    "RouteStop",
    "Run",
    "RunStop",
    "Fare",
    "Reservation",
    "Ticket",
    "SeatOccupancy",
    "Payment",
    "Refund",
    "BoardingCheck",
]
