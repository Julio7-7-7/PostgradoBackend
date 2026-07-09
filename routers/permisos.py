from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.permiso import Permiso
from schemas.admin import PermisoResponse
from dependencies import get_current_user, require_permiso
from schemas.auth import UserResponse

router = APIRouter(prefix="/permisos", tags=["Permisos"])


@router.get("", response_model=list[PermisoResponse])
def listar_permisos(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("roles.gestionar")),
):
    return db.query(Permiso).order_by(Permiso.codigo).all()
