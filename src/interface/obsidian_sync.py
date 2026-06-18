import asyncio
import logging
import os
import re
import time

from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

PENDING_TAG = "#task/pending"
ACTIVE_TAG = "#task/active"


class TaskWatcher(FileSystemEventHandler):
    """Watches a vault for Markdown task files and queues pending tasks.

    watchdog dispatches events on its own observer thread, so events are
    handed back to the asyncio loop via ``call_soon_threadsafe``.
    """

    def __init__(self, queue: asyncio.Queue, debounce_seconds: float = 2.0):
        self.queue = queue
        self.debounce_seconds = debounce_seconds
        self.last_triggered: dict[str, float] = {}
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None

    # --- watchdog callbacks -------------------------------------------------

    def on_modified(self, event):
        self._handle(event)

    def on_created(self, event):
        self._handle(event)

    # --- internals ----------------------------------------------------------

    def _handle(self, event):
        if getattr(event, "is_directory", False):
            return
            
        path = os.path.normpath(event.src_path)
        if not path.endswith(".md"):
            return
            
        now = time.monotonic()
        last = self.last_triggered.get(path)
        if last is not None and (now - last) < self.debounce_seconds:
            logger.debug("Debounced event for %s", path)
            return
            
        # Introduce a tiny 100ms sleep to let Obsidian/Windows flush its initial write lock
        time.sleep(0.1)
        
        self.last_triggered[path] = now
        logger.info("Processing change for %s", path)
        
        content = None
        # Robust Read with retries for Windows locks
        for attempt in range(5):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                break
            except OSError as exc:
                if attempt == 4:
                    logger.warning("Could not read %s: %s", path, exc)
                    return
                # Backoff 100ms before retrying
                time.sleep(0.1)
                
        if PENDING_TAG not in content:
            logger.debug("No pending task tag in %s, ignoring", path)
            return
            
        updated = content.replace(PENDING_TAG, ACTIVE_TAG)
        
        # Robust Write with retries for Windows locks
        success = False
        for attempt in range(5):
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(updated)
                success = True
                break
            except OSError as exc:
                if attempt == 4:
                    logger.warning("Could not update %s: %s", path, exc)
                    return
                # Backoff 100ms before retrying
                time.sleep(0.1)
                
        if success:
            targets = self._parse_target_files(updated)
            logger.info("Activated task in %s with %d target(s)", path, len(targets))
            self._enqueue({"file_path": path, "targets": targets})

    def _enqueue(self, item: dict):
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, item)
        else:
            # No loop captured (e.g. constructed outside async context).
            self.queue.put_nowait(item)
        logger.debug("Queued task: %s", item)

    @staticmethod
    def _parse_target_files(content: str) -> list:
        """Extract the 'Target Files' list from the Markdown body.

        Supports a header/label followed by a bullet list, e.g.::

            ## Target Files
            - src/foo.py
            - src/bar.py

        and an inline list, e.g.``Target Files: [src/foo.py, src/bar.py]``.
        """
        lines = content.splitlines()
        for i, line in enumerate(lines):
            match = re.match(r"^\s*#*\s*\**\s*Target Files\s*\**\s*:?\s*(.*)$", line, re.IGNORECASE)
            if not match:
                continue

            inline = match.group(1).strip()
            if inline:
                inline = inline.strip("[]")
                return [t.strip().strip("`\"'") for t in inline.split(",") if t.strip()]

            # Otherwise collect the following bullet-list items.
            targets = []
            for following in lines[i + 1:]:
                bullet = re.match(r"^\s*[-*+]\s+(.*\S)\s*$", following)
                if bullet:
                    targets.append(bullet.group(1).strip().strip("`\"'"))
                elif following.strip() == "":
                    continue
                else:
                    break
            return targets

        return []
