import asyncio
import logging

from dotenv import load_dotenv

load_dotenv()

from watchdog.observers import Observer

from src.core.state import AgentOrchestrator, TaskContext
from src.interface.obsidian_sync import TaskWatcher
from src.memory.graph_manager import CodeGraph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

WATCH_PATH = "./test_vault/01_Active_Tasks/"


async def process_queue(queue: asyncio.Queue):
    """Consume queued task items forever, running the agent loop for each."""
    while True:
        task_data = await queue.get()
        try:
            logger.info("Picked up task: %s", task_data.get("file_path"))

            context = TaskContext(
                description=task_data.get("file_path", ""),
                affected_files=task_data.get("targets", []),
            )

            orchestrator = AgentOrchestrator(context)
            await orchestrator.run_loop()

            logger.info("Finished task: %s", task_data.get("file_path"))
        except Exception:
            logger.exception("Error processing task: %s", task_data)
        finally:
            queue.task_done()


async def main():
    queue: asyncio.Queue = asyncio.Queue()

    # Shared code graph for the session (passed to orchestration as it grows).
    code_graph = CodeGraph()  # noqa: F841 - reserved for orchestrator wiring

    # Constructed inside the running loop so TaskWatcher captures it for
    # thread-safe enqueueing from the observer thread.
    event_handler = TaskWatcher(queue)

    observer = Observer()
    observer.schedule(event_handler, WATCH_PATH, recursive=True)
    observer.start()
    logger.info("Watching %s for task files...", WATCH_PATH)

    try:
        await process_queue(queue)
    finally:
        observer.stop()
        # Join the observer thread off the event loop to avoid blocking it.
        await asyncio.to_thread(observer.join)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down.")
