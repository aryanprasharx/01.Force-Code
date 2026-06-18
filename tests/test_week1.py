import asyncio
from src.core.state import TaskContext, AgentState, AgentOrchestrator
from src.core.router import route_task

async def run_week1_tests():
    print("--- TESTING ROUTER ---")
    assert route_task("Fix typo in readme", 1) == "LOCAL_TIER_1"
    assert route_task("Refactor the database schema", 2) == "CLOUD_TIER_2"
    assert route_task("Implement critical security patch", 5) == "CLOUD_TIER_3"
    print("✅ Router logic passed.")

    print("\n--- TESTING STATE MACHINE ---")
    context = TaskContext(
        description="Test task",
        affected_files=["main.py"]
    )
    orchestrator = AgentOrchestrator(context)
    
    # Test transition
    await orchestrator.transition_to(AgentState.PLANNING)
    assert orchestrator.context.current_state == AgentState.PLANNING
    assert len(orchestrator.context.logs) == 1
    
    # Test max retries enforcement
    orchestrator.context.iteration_count = 4 # Exceeds default max_retries of 3
    await orchestrator.run_loop()
    assert orchestrator.context.current_state == AgentState.AWAITING_USER
    print("✅ State Machine transitions and retry limits passed.")

if __name__ == "__main__":
    asyncio.run(run_week1_tests())