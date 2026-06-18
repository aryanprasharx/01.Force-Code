import json

import networkx as nx


class CodeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_file_node(self, filepath: str):
        self.graph.add_node(filepath)

    def add_dependency(self, source_file: str, target_file: str):
        self.graph.add_edge(source_file, target_file)

    def save_to_json(self, filepath: str):
        data = nx.node_link_data(self.graph, edges="links")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_from_json(self, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.graph = nx.node_link_graph(data, directed=True, edges="links")

    def get_semantic_context(self, target_file: str) -> str:
        if target_file not in self.graph:
            return f"Module [{target_file}] not found in the code graph."

        successors = list(self.graph.successors(target_file))
        predecessors = list(self.graph.predecessors(target_file))

        depends_on = ", ".join(successors) if successors else "nothing"
        used_by = ", ".join(predecessors) if predecessors else "nothing"

        return (
            f"Module [{target_file}] depends on [{depends_on}]. "
            f"Module [{target_file}] is used by [{used_by}]."
        )
