import asyncio
import logging
import os
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
            task_file = task_data.get("file_path")
            logger.info("Picked up task: %s", task_file)
            
            # READ THE ACTUAL TASK SPECIFICATION CONTENT
            if os.path.exists(task_file):
                with open(task_file, "r", encoding="utf-8") as f:
                    markdown_spec = f.read()
            else:
                markdown_spec = f"Task File missing. Resolve file at: {task_file}"

            context = TaskContext(
                description=markdown_spec,  # Context amnesia resolved
                affected_files=task_data.get("targets", []),
            )
            
            orchestrator = AgentOrchestrator(context)
            await orchestrator.run_loop()
            
            logger.info("Finished task: %s", task_file)
        except Exception as e:
            logger.exception("Error processing task: %s", task_data)
        finally:
            queue.task_done()

async def main():
    # Ensure active watch directory exists
    os.makedirs(WATCH_PATH, exist_ok=True)
    
    queue: asyncio.Queue = asyncio.Queue()
    code_graph = CodeGraph()
    
    event_handler = TaskWatcher(queue)
    observer = Observer()
    observer.schedule(event_handler, WATCH_PATH, recursive=True)
    observer.start()
    logger.info("Watching %s for task files...", WATCH_PATH)
    
    try:
        await process_queue(queue)
    finally:
        observer.stop()
        await asyncio.to_thread(observer.join)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down.")