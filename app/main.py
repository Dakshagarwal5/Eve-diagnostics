from fastapi import FastAPI

from .database import Base, engine
from .routers import auth_router, centres_router, bookings_router, payments_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EVE Healthcare - Diagnostic Bookings API")

app.include_router(auth_router.router)
app.include_router(centres_router.router)
app.include_router(bookings_router.router)
app.include_router(payments_router.router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
