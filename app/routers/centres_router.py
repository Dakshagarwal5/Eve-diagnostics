from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/centres", tags=["centres"])


@router.post("/", response_model=schemas.CentreOut, status_code=201)
def create_centre(
    payload: schemas.CentreCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # Any authenticated user can add a centre in this simple version.
    # In a real system this would be restricted to an admin role.
    centre = models.DiagnosticCentre(name=payload.name, location=payload.location)
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


@router.get("/", response_model=list[schemas.CentreOut])
def list_centres(db: Session = Depends(get_db)):
    return db.query(models.DiagnosticCentre).all()


@router.get("/{centre_id}", response_model=schemas.CentreOut)
def get_centre(centre_id: str, db: Session = Depends(get_db)):
    centre = db.query(models.DiagnosticCentre).filter(models.DiagnosticCentre.id == centre_id).first()
    if not centre:
        raise HTTPException(status_code=404, detail="Centre not found")
    return centre


@router.post("/{centre_id}/tests", response_model=schemas.TestOut, status_code=201)
def add_test(
    centre_id: str,
    payload: schemas.TestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    centre = db.query(models.DiagnosticCentre).filter(models.DiagnosticCentre.id == centre_id).first()
    if not centre:
        raise HTTPException(status_code=404, detail="Centre not found")

    test = models.DiagnosticTest(name=payload.name, price=payload.price, centre_id=centre.id)
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.get("/{centre_id}/tests", response_model=list[schemas.TestOut])
def list_tests(centre_id: str, db: Session = Depends(get_db)):
    centre = db.query(models.DiagnosticCentre).filter(models.DiagnosticCentre.id == centre_id).first()
    if not centre:
        raise HTTPException(status_code=404, detail="Centre not found")
    return centre.tests
