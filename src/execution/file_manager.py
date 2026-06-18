import os
import shutil
import logging

logger = logging.getLogger(__name__)

def apply_full_overwrite(filepath: str, new_content: str) -> None:
    """Copies the existing file to filepath + '.bak' before overwriting."""
    filepath = os.path.normpath(filepath)
    if os.path.exists(filepath):
        bak_path = filepath + ".bak"
        shutil.copy2(filepath, bak_path)
        logger.info(f"Created backup: {bak_path}")
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    logger.info(f"Overwrote file: {filepath}")

def lock_file(filepath: str) -> None:
    """Creates an empty .agent_lock file next to the targeted file."""
    lock_path = os.path.normpath(filepath + ".agent_lock")
    with open(lock_path, "w", encoding="utf-8") as f:
        f.write("")
    logger.info(f"Locked file: {filepath}")

def unlock_file(filepath: str) -> None:
    """Deletes the .agent_lock file if it exists."""
    lock_path = os.path.normpath(filepath + ".agent_lock")
    if os.path.exists(lock_path):
        os.remove(lock_path)
        logger.info(f"Unlocked file: {filepath}")
    else:
        logger.warning(f"Attempted to unlock file that wasn't locked: {lock_path}")