import yaml
from pydantic import BaseModel


# This describes what one item on the map must look like.
# Pydantic checks every item against it and complains if something's off.
class Node(BaseModel):
    id: str
    label: str
    tier: str
    single_source: bool = False
    geo_concentration: str = "low"
    depends_on: list[str] = []
    direct_risk: float = 0.0


def load_graph(path="data/dependency_graph.yaml"):
    # 1. Read the YAML file and turn it into plain Python data.
    with open(path) as f:
        raw = yaml.safe_load(f)

    # 2. Turn each item into a checked Node, stored by its id for easy lookup.
    graph = {}
    for item in raw["nodes"]:
        node = Node(**item)
        graph[node.id] = node

    # 3. Safety check: every "depends_on" must point to a real item.
    for node in graph.values():
        for dep in node.depends_on:
            if dep not in graph:
                raise ValueError(
                    f"'{node.id}' depends on '{dep}', but '{dep}' isn't in the map."
                )

    return graph

def propagate(node_id, graph, decay=0.6, memo=None):
    # memo remembers nodes we've already figured out, so we never redo work.
    if memo is None:
        memo = {}
    if node_id in memo:
        return memo[node_id]

    node = graph[node_id]

    # The worst risk coming from anything this item depends on (upstream).
    upstream_risk = 0.0
    for dep in node.depends_on:
        upstream_risk = max(upstream_risk, propagate(dep, graph, decay, memo))

    # This item's own risk = its direct hit, plus a faded share of upstream risk.
    risk = node.direct_risk + decay * upstream_risk

    # No backup supplier? The blow lands harder.
    if node.single_source:
        risk = risk * 1.5

    # Risk never goes above 1.0 (100%).
    risk = min(risk, 1.0)

    memo[node_id] = risk
    return risk    


# This part runs only when you do `python graph.py` directly.
if __name__ == "__main__":
    graph = load_graph()

    # SIMULATE A SHOCK: pretend the news reports a serious neon shortage.
    graph["neon_gas"].direct_risk = 0.8
    print("Shock applied: neon_gas direct_risk = 0.8\n")

    # Now see how exposed everything is, worst first.
    results = []
    for node_id in graph:
        results.append((node_id, propagate(node_id, graph)))
    results.sort(key=lambda pair: pair[1], reverse=True)

    print("Risk score for each item (0.0 = calm, 1.0 = critical):\n")
    for node_id, risk in results:
        bar = "#" * int(risk * 20)
        print(f"  {risk:0.2f}  {bar:<20}  {graph[node_id].label}")