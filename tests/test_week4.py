import asyncio
import os
import time
from src.execution.file_manager import apply_full_overwrite, lock_file, unlock_file
# Assuming you have a way to import or mock the Watchdog queue logic here

def run_week4_tests():
    print("--- TESTING FILE MANAGER ---")
    test_file = "dummy_target.py"
    
    try:
        # 1. Create dummy file
        with open(test_file, "w") as f:
            f.write("original content")
            
        # 2. Test Locking
        lock_file(test_file)
        assert os.path.exists(f"{test_file}.agent_lock")
        
        # 3. Test Overwrite & Backup
        apply_full_overwrite(test_file, "new content")
        assert os.path.exists(f"{test_file}.bak")
        
        with open(test_file, "r") as f:
            assert f.read() == "new content"
            
        with open(f"{test_file}.bak", "r") as f:
            assert f.read() == "original content"
            
        # 4. Test Unlocking
        unlock_file(test_file)
        assert not os.path.exists(f"{test_file}.agent_lock")
        
        print("✅ File locking, overwriting, and backups passed.")
        
    finally:
        # Cleanup
        for f in [test_file, f"{test_file}.bak", f"{test_file}.agent_lock"]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    run_week4_tests()