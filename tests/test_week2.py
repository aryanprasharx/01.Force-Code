import os
import shutil
from src.memory.graph_manager import CodeGraph
from src.memory.ast_parser import build_graph_from_directory

def run_week2_tests():
    print("--- TESTING GRAPHRAG & AST PARSER ---")
    test_dir = "./mock_project"
    os.makedirs(test_dir, exist_ok=True)
    
    try:
        # Create mock codebase
        with open(f"{test_dir}/utils.py", "w") as f:
            f.write("def helper(): pass\n")
        with open(f"{test_dir}/main.py", "w") as f:
            f.write("from utils import helper\nimport os\nhelper()\n")
            
        # Initialize and build graph
        graph = CodeGraph()
        build_graph_from_directory(test_dir, graph)
        
        # Test JSON serialization
        graph.save_to_json(f"{test_dir}/graph.json")
        assert os.path.exists(f"{test_dir}/graph.json")
        
        # Test Semantic Context
        # Note: Paths might need normalization depending on your OS (\\ vs /)
        main_path = os.path.normpath(f"{test_dir}/main.py")
        utils_path = os.path.normpath(f"{test_dir}/utils.py")
        
        context_str = graph.get_semantic_context(main_path)
        print(f"Generated Context:\n{context_str}")
        
        assert utils_path in context_str or "utils.py" in context_str
        print("✅ GraphRAG parsing and semantic context passed.")
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    run_week2_tests()