import logging
from e2b_code_interpreter import AsyncSandbox

# Note: In E2B v2, the command execution exceptions are captured cleanly in the result object,
# so we no longer need the fragile CommandExitException try/except block.

logger = logging.getLogger(__name__)

class E2BRunner:
    """Runs a project's test suite inside an isolated E2B v2 sandbox."""
    
    async def run_tests(self, code_files: dict[str, str], test_command: str) -> dict:
        sandbox = None
        try:
            # E2B v2 Async Initialization
            sandbox = await AsyncSandbox.create()
            
            # Write each source file into the sandbox filesystem
            for path, content in code_files.items():
                await sandbox.files.write(path, content)
            
            # Execute the test command using E2B v2 commands API
            # commands.run() executes and cleanly returns exit_code, stdout, and stderr
            result = await sandbox.commands.run(test_command)
            
            return {
                "success": result.exit_code == 0,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            
        except Exception as exc:
            logger.error(f"E2B execution failed: {exc}")
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(exc),
            }
            
        finally:
            if sandbox is not None:
                # E2B v2 termination
                await sandbox.kill()