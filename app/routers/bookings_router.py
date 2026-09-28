from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db
from ..models import BookingStatus

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=schemas.BookingOut, status_code=201)
def create_booking(
    payload: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    test = db.query(models.DiagnosticTest).filter(models.DiagnosticTest.id == payload.test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test.centre_id != payload.centre_id:
        raise HTTPException(status_code=400, detail="Test does not belong to the given centre")

    booking = models.Booking(
        user_id=current_user.id,
        test_id=test.id,
        centre_id=payload.centre_id,
        appointment_time=payload.appointment_time,
        amount=test.price,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/", response_model=list[schemas.BookingOut])
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.Booking).filter(models.Booking.user_id == current_user.id).all()


@router.get("/{booking_id}", response_model=schemas.BookingOut)
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    booking = _get_owned_booking(booking_id, db, current_user)
    return booking


@router.post("/{booking_id}/cancel", response_model=schemas.BookingOut)
def cancel_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    booking = _get_owned_booking(booking_id, db, current_user)
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only PENDING bookings can be cancelled")

    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking


def _get_owned_booking(booking_id: str, db: Session, current_user: models.User) -> models.Booking:
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this booking")
    return booking
