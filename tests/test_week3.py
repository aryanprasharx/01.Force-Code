import asyncio
import os
from dotenv import load_dotenv
from src.execution.sandbox import E2BRunner
from src.llm.clients import GeminiClient, LocalOpenVINOClient

load_dotenv()

async def run_week3_tests():
    print("--- TESTING E2B SANDBOX ---")
    runner = E2BRunner()
    
    # Test 1: Passing Code
    passing_code = {"test.py": "print('Hello from E2B')"}
    result_pass = await runner.run_tests(passing_code, "python test.py")
    assert result_pass["success"] is True
    # UPDATED CONTRACT KEY TO STDOUT
    assert "Hello from E2B" in result_pass["stdout"]
    print("✅ E2B Passing execution verified.")
    
    # Test 2: Failing Code (Syntax Error)
    failing_code = {"test_fail.py": "print('Missing quote)"}
    result_fail = await runner.run_tests(failing_code, "python test_fail.py")
    assert result_fail["success"] is False
    # UPDATED CONTRACT KEY TO STDERR
    assert "SyntaxError" in result_fail["stderr"]
    print("✅ E2B Error capture verified.")

    print("\n--- TESTING LLM CLIENTS ---")
    # Test Mock Local
    local_client = LocalOpenVINOClient()
    local_res = await local_client.generate("Hello", "System")
    assert local_res == "MOCK_LOCAL_RESPONSE"
    
    # Test Gemini (if key exists)
    if os.getenv("GEMINI_API_KEY"):
        gemini = GeminiClient()
        gemini_res = await gemini.generate("Say the word 'Acknowledge'", "You are a helpful bot.")
        assert "Acknowledge" in gemini_res or "acknowledge" in gemini_res.lower()
        print("✅ Gemini API connection verified.")
    else:
        print("⚠️ Skipping Gemini test (No API key found).")

if __name__ == "__main__":
    asyncio.run(run_week3_tests())