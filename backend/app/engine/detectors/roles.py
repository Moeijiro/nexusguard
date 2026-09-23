"""Privileged role grants.

Flags a role that carries a dangerous permission (Administrator, Manage
Server/Roles/Channels/Webhooks, Ban, Kick, Mention Everyone) being given to a
member. It never reverts the change: a legitimate promotion looks exactly the
same, so a human decides.

Severity:
    role includes ADMINISTRATOR             -> critical
    any other dangerous permission          -> high
"""

from __future__ import annotations

from app.core import permissions
from app.engine.detectors.base import Detection, EventType
from app.engine.events import RoleGrantEvent
from app.engine.rules_schema import Module, PrivilegedRolesRule
from app.engine.severity import Severity
from app.engine.state import WindowStore


class PrivilegedRoleDetector:
    module = Module.PRIVILEGED_ROLES
    handles = (RoleGrantEvent,)

    def detect(self, event: RoleGrantEvent, rule: PrivilegedRolesRule, state: WindowStore) -> Detection | None:
        dangerous = permissions.dangerous_flags(event.role_permissions)
        if not dangerous:
            return None
        severity = Severity.CRITICAL if "ADMINISTRATOR" in dangerous else Severity.HIGH
        by = f" by {event.granted_by.name}" if event.granted_by else ""
        return Detection(
            module=self.module,
            type=EventType.ROLE_CHANGE,
            severity=severity,
            summary=f"@{event.role_name} granted{by}",
            user=event.member,
            metadata={
                "role_id": event.role_id,
                "role_name": event.role_name,
                "permissions": dangerous,
                "granted_by": event.granted_by.name if event.granted_by else None,
            },
        )
