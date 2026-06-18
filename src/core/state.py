from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    CODING = "CODING"
    TESTING = "TESTING"
    ESCALATING = "ESCALATING"
    AWAITING_USER = "AWAITING_USER"


class TaskContext(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    description: str
    affected_files: list[str] = Field(default_factory=list)
    current_state: AgentState = AgentState.IDLE
    iteration_count: int = 0
    max_retries: int = 3
    logs: list[str] = Field(default_factory=list)


class AgentOrchestrator:
    def __init__(self, context: TaskContext) -> None:
        self.context = context

    async def transition_to(self, new_state: AgentState) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        self.context.logs.append(
            f"[{timestamp}] {self.context.current_state.value} -> {new_state.value}"
        )
        self.context.current_state = new_state

    async def run_loop(self) -> None:
        if self.context.iteration_count > self.context.max_retries:
            await self.transition_to(AgentState.AWAITING_USER)

        match self.context.current_state:
            case AgentState.IDLE:
                print("State: IDLE - waiting to start.")
            case AgentState.PLANNING:
                print("State: PLANNING - building a plan.")
            case AgentState.CODING:
                print("State: CODING - writing code.")
            case AgentState.TESTING:
                print("State: TESTING - running tests.")
            case AgentState.ESCALATING:
                print("State: ESCALATING - escalating the issue.")
            case AgentState.AWAITING_USER:
                print("State: AWAITING_USER - waiting for user input.")
            case _:
                pass
