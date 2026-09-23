"""The action engine: one small module per Discord action."""

from collections.abc import Awaitable, Callable

from app.engine.actions import delete_message, flag, kick, notify, restrict, timeout, warn
from app.engine.actions.base import ActionContext, ActionResult, Status
from app.engine.rules_schema import ActionName

HANDLERS: dict[ActionName, Callable[[ActionContext], Awaitable[ActionResult]]] = {
    ActionName.DELETE_MESSAGE: delete_message.run,
    ActionName.WARN: warn.run,
    ActionName.TIMEOUT: timeout.run,
    ActionName.RESTRICT: restrict.run,
    ActionName.KICK: kick.run,
    ActionName.FLAG: flag.run,
    ActionName.NOTIFY: notify.run,
}

# Actions that change a member's standing are written to the moderation log.
MODERATION_ACTIONS = {ActionName.WARN, ActionName.TIMEOUT, ActionName.RESTRICT, ActionName.KICK}

__all__ = ["HANDLERS", "MODERATION_ACTIONS", "ActionContext", "ActionResult", "Status"]
