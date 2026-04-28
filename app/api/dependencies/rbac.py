from fastapi import HTTPException, Depends, status
from app.models.users import User, ROLE
from app.api.dependencies.deps import get_current_user


class Rolechecker:
    def __init__(self, required_role: ROLE):
        self.required_role = required_role

    def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role == ROLE.ADMIN:
            return current_user
            
        if current_user.role != self.required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    