import random
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db
from ..models import BookingStatus, PaymentStatus

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=schemas.PaymentOut, status_code=201)
def simulate_payment(
    payload: schemas.PaymentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    booking = db.query(models.Booking).filter(models.Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay for this booking")
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail="Booking is not in a payable state")

    # Simulate a payment provider: 80% chance of success.
    result = PaymentStatus.SUCCESS if random.random() < 0.8 else PaymentStatus.FAILED
    event_id = str(uuid.uuid4())  # stands in for the provider's unique payment/event id

    return _apply_payment_event(db, booking, event_id, result)


@router.post("/webhook/", response_model=schemas.PaymentOut)
def payment_webhook(payload: schemas.WebhookRequest, db: Session = Depends(get_db)):
    """
    Simulated payment-provider webhook. Idempotent: if `event_id` was already
    processed, the existing result is returned as-is and nothing is re-applied,
    so retried/duplicate webhook deliveries can never double-process a booking.
    """
    if payload.status not in (PaymentStatus.SUCCESS.value, PaymentStatus.FAILED.value):
        raise HTTPException(status_code=400, detail="status must be SUCCESS or FAILED")

    existing = db.query(models.Payment).filter(models.Payment.event_id == payload.event_id).first()
    if existing:
        return existing

    booking = db.query(models.Booking).filter(models.Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    return _apply_payment_event(db, booking, payload.event_id, PaymentStatus(payload.status))


def _apply_payment_event(
    db: Session, booking: models.Booking, event_id: str, result: PaymentStatus
) -> models.Payment:
    payment = models.Payment(booking_id=booking.id, event_id=event_id, status=result)
    db.add(payment)

    if booking.status == BookingStatus.PENDING:
        booking.status = BookingStatus.CONFIRMED if result == PaymentStatus.SUCCESS else BookingStatus.FAILED

    try:
        db.commit()
    except IntegrityError:
        # Race condition: two requests processed the same event_id at once.
        # Whichever lost the race just returns the already-committed row.
        db.rollback()
        return db.query(models.Payment).filter(models.Payment.event_id == event_id).first()

    db.refresh(payment)
    return payment
