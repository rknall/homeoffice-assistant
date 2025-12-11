# src/services/rbac_seed_service.py
from sqlalchemy.orm import Session

from src.models import Permission, Role, RolePermission
from src.rbac.permissions import CORE_PERMISSIONS
from src.rbac.roles import DEFAULT_ROLES

from . import rbac_service


def seed_rbac_data(db: Session) -> None:
    """Seeds the database with core permissions and default roles.

    This function is idempotent.
    @param db: SQLAlchemy Session object
    """
    # Seed permissions
    for perm_data in CORE_PERMISSIONS:
        permission = (
            db.query(Permission).filter(Permission.code == perm_data["code"]).first()
        )
        if not permission:
            rbac_service.register_permission(db, **perm_data)

    # Seed roles and role-permissions
    for role_data in DEFAULT_ROLES:
        role = rbac_service.get_role_by_name(db, role_data["name"])
        if not role:
            role = Role(
                name=role_data["name"],
                is_system=role_data["is_system"],
                description=role_data["description"],
            )
            db.add(role)
            db.flush()  # Flush to get the role ID

            for perm_code in role_data["permissions"]:
                permission = (
                    db.query(Permission).filter(Permission.code == perm_code).first()
                )
                if permission:
                    role_permission = RolePermission(
                        role_id=role.id, permission_code=permission.code
                    )
                    db.add(role_permission)
    db.commit()
