from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Centres & Tests ----------
class TestCreate(BaseModel):
    name: str
    price: float = Field(gt=0)


class TestOut(BaseModel):
    id: str
    name: str
    price: float

    class Config:
        from_attributes = True


class CentreCreate(BaseModel):
    name: str
    location: str


class CentreOut(BaseModel):
    id: str
    name: str
    location: str
    tests: list[TestOut] = []

    class Config:
        from_attributes = True


# ---------- Bookings ----------
class BookingCreate(BaseModel):
    test_id: str
    centre_id: str
    appointment_time: datetime


class BookingOut(BaseModel):
    id: str
    test_id: str
    centre_id: str
    appointment_time: datetime
    amount: float
    status: str

    class Config:
        from_attributes = True


# ---------- Payments ----------
class PaymentRequest(BaseModel):
    booking_id: str


class PaymentOut(BaseModel):
    id: str
    booking_id: str
    status: str

    class Config:
        from_attributes = True


class WebhookRequest(BaseModel):
    event_id: str
    booking_id: str
    status: str  # "SUCCESS" or "FAILED"
