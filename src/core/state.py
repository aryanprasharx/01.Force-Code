from __future__ import annotations
import os
import logging
import asyncio
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from src.execution.file_manager import apply_full_overwrite, lock_file, unlock_file
from src.execution.sandbox import E2BRunner
from src.llm.clients import GeminiClient, LocalOpenVINOClient

logger = logging.getLogger(__name__)

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

def extract_code(text: str) -> str:
    """Safely extracts Python code from markdown code blocks."""
    if "```python" in text:
        return text.split("```python")[1].split("```")[0].strip()
    elif "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text.strip()

class AgentOrchestrator:
    def __init__(self, context: TaskContext, llm_client=None, sandbox_runner=None) -> None:
        self.context = context
        self.llm_client = llm_client or GeminiClient()
        self.sandbox_runner = sandbox_runner or E2BRunner()
        self.generated_code = ""

    async def transition_to(self, new_state: AgentState) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        self.context.logs.append(
            f"[{timestamp}] {self.context.current_state.value} -> {new_state.value}"
        )
        self.context.current_state = new_state
        logger.info(f"Transitioned to {new_state.value}")

    async def run_loop(self) -> None:
        """The main continuous state execution loop."""
        # Force start from IDLE to PLANNING
        if self.context.current_state == AgentState.IDLE:
            await self.transition_to(AgentState.PLANNING)

        while True:
            # 1. Safety Check: Max Retries
            if self.context.iteration_count > self.context.max_retries:
                logger.warning("❌ Max retries exceeded. Halting task.")
                await self.transition_to(AgentState.AWAITING_USER)
                break

            # 2. State Switchboard
            match self.context.current_state:
                case AgentState.PLANNING:
                    logger.info("Executing PLANNING State...")
                    
                    # Read current file states for context
                    context_files = ""
                    for filepath in self.context.affected_files:
                        norm_path = os.path.normpath(filepath)
                        lock_file(norm_path)
                        if os.path.exists(norm_path):
                            with open(norm_path, "r", encoding="utf-8") as f:
                                context_files += f"\n### File: {filepath}\n{f.read()}\n"
                        else:
                            context_files += f"\n### File: {filepath} (Does not exist yet, you must create it)\n"

                    # Instruct the model to implement the spec and write self-tests
                    system_prompt = (
                        "You are an expert test-driven software engineer. You must implement the requested feature. "
                        "CRITICAL: You must append a self-verifying 'if __name__ == \"__main__\":' block at the bottom of the file "
                        "containing assertions that prove your implementation meets the task's success criteria. "
                        "Output ONLY valid, executable Python code inside a markdown block. No prose."
                    )
                    prompt = (
                        f"Task Specification:\n{self.context.description}\n\n"
                        f"Current Codebase Context:\n{context_files}\n\n"
                        f"Write the complete, updated Python code for the target files."
                    )

                    try:
                        response = await self.llm_client.generate(prompt, system_prompt)
                        self.generated_code = extract_code(response)
                        await self.transition_to(AgentState.CODING)
                    except Exception as e:
                        logger.error(f"Planning generation failed: {e}")
                        await self.transition_to(AgentState.ESCALATING)
                        break

                case AgentState.CODING:
                    logger.info("Executing CODING State...")
                    if self.context.affected_files:
                        target = os.path.normpath(self.context.affected_files[0])
                        try:
                            apply_full_overwrite(target, self.generated_code)
                            await self.transition_to(AgentState.TESTING)
                        except Exception as e:
                            logger.error(f"Writing file changes failed: {e}")
                            await self.transition_to(AgentState.ESCALATING)
                            break
                    else:
                        logger.error("No affected files specified!")
                        await self.transition_to(AgentState.AWAITING_USER)
                        break

                case AgentState.TESTING:
                    logger.info("Executing TESTING State...")
                    code_files = {}
                    for filepath in self.context.affected_files:
                        norm_path = os.path.normpath(filepath)
                        if os.path.exists(norm_path):
                            with open(norm_path, "r", encoding="utf-8") as f:
                                code_files[filepath] = f.read()

                    target = self.context.affected_files[0]
                    # Run the file directly; python will execute the __main__ self-tests
                    result = await self.sandbox_runner.run_tests(code_files, f"python {target}")

                    # Clean up: Unlock files
                    for filepath in self.context.affected_files:
                        unlock_file(os.path.normpath(filepath))

                    if result["success"]:
                        logger.info("🎉 Sandbox tests passed successfully! Task complete.")
                        await self.transition_to(AgentState.IDLE)
                        break
                    else:
                        logger.warning(f"❌ Sandbox tests failed! Retrying. Errors found:\n{result['stderr']}")
                        self.context.iteration_count += 1
                        self.context.logs.append(f"Iteration {self.context.iteration_count} Failure:\n{result['stderr']}")
                        
                        # Inject the failure back into the task description for self-correction
                        self.context.description += f"\n\n### Prior Test Failure (Fix This):\n{result['stderr']}"
                        await self.transition_to(AgentState.PLANNING)

                case AgentState.ESCALATING:
                    logger.warning("Task execution failed on multiple layers. Escalating to user.")
                    await self.transition_to(AgentState.AWAITING_USER)
                    break

                case AgentState.AWAITING_USER:
                    logger.info("Awaiting user input...")
                    break