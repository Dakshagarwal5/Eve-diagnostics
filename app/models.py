import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, ForeignKey, DateTime, Enum, UniqueConstraint
)
from sqlalchemy.orm import relationship

from .database import Base


def gen_uuid():
    return str(uuid.uuid4())


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    bookings = relationship("Booking", back_populates="user")


class DiagnosticCentre(Base):
    __tablename__ = "centres"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)

    tests = relationship("DiagnosticTest", back_populates="centre", cascade="all, delete-orphan")


class DiagnosticTest(Base):
    __tablename__ = "tests"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    centre_id = Column(String, ForeignKey("centres.id"), nullable=False)

    centre = relationship("DiagnosticCentre", back_populates="tests")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    test_id = Column(String, ForeignKey("tests.id"), nullable=False)
    centre_id = Column(String, ForeignKey("centres.id"), nullable=False)
    appointment_time = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    test = relationship("DiagnosticTest")
    centre = relationship("DiagnosticCentre")
    payments = relationship("Payment", back_populates="booking")


class Payment(Base):
    """
    One row per processed payment event. `event_id` is what makes the
    webhook idempotent: it has a unique constraint, so the same event
    can never be applied twice.
    """
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=gen_uuid)
    booking_id = Column(String, ForeignKey("bookings.id"), nullable=False)
    event_id = Column(String, nullable=False)  # id of the payment/webhook event
    status = Column(Enum(PaymentStatus), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    booking = relationship("Booking", back_populates="payments")

    __table_args__ = (UniqueConstraint("event_id", name="uq_payment_event_id"),)
