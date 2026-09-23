"""Put the member in the dashboard review queue. Nothing is sent to Discord."""

from __future__ import annotations

from app.engine.actions.base import ActionContext, ActionResult, Status
from app.engine.rules_schema import ActionName


async def run(ctx: ActionContext) -> ActionResult:
    # The Store turns this into a flag row when it records the outcome.
    return ActionResult(ActionName.FLAG, Status.DONE, "Flagged for review")
