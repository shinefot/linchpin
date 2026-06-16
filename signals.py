import json
from dotenv import load_dotenv
from anthropic import Anthropic

from graph import load_graph, propagate

load_dotenv()
client = Anthropic()


# ---- One reusable agent. The only thing that changes between the three
# ---- specialists is the "name" and the "focus" we hand it. ----
def run_agent(graph, name, focus, model="claude-sonnet-4-6"):
    item_lines = [f"- {node.id}: {node.label}" for node in graph.values()]
    items_text = "\n".join(item_lines)

    prompt = f"""You are a {name}. Below is a list of items we monitor ("id: name"):

{items_text}

{focus}

Report ONLY what you actually found, as a JSON array. Each finding shaped exactly like:
[{{"node_id": "<one id from the list>", "severity": <number 0 to 1>, "reason": "<one short sentence>"}}]

Severity guide: 0.2 = minor, 0.5 = moderate, 0.8 = serious, 1.0 = supply halted.
Only include items with credible recent news. If nothing, return [].
Output the JSON array and NOTHING else.
"""

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        return []
    return json.loads(text[start:end + 1])


# ---- The three specialists. Same machine, three different jobs. ----
AGENTS = [
    {
        "name": "supply-disruption news analyst",
        "focus": "Search recent news (last ~6 months) for factory outages, fires, accidents, shortages, or capacity cuts affecting any item or the raw materials it depends on.",
    },
    {
        "name": "trade and export-control analyst",
        "focus": "Search for recent export controls, sanctions, tariffs, or licensing rules affecting any item or its raw materials (for example gallium, germanium, rare earths, neon).",
    },
    {
        "name": "raw-materials and commodity analyst",
        "focus": "Search for recent price spikes, mine or refinery disruptions, or output changes in the raw materials these items depend on.",
    },
]


def gather_all_signals(graph):
    all_findings = []
    for agent in AGENTS:
        print(f"Running: {agent['name']} ...")
        findings = run_agent(graph, agent["name"], agent["focus"])
        print(f"   found {len(findings)} signal(s)")
        for f in findings:
            f["agent"] = agent["name"]      # remember who found it
        all_findings.extend(findings)
    return all_findings


def apply_findings(graph, findings):
    for node in graph.values():            # start everything calm
        node.direct_risk = 0.0
    notes = {}                              # node_id -> list of (severity, reason, agent)
    for f in findings:
        nid = f.get("node_id")
        if nid not in graph:
            continue
        sev = min(max(float(f["severity"]), 0.0), 1.0)
        graph[nid].direct_risk = max(graph[nid].direct_risk, sev)   # keep the WORST
        notes.setdefault(nid, []).append((sev, f["reason"], f.get("agent", "")))
    return notes


if __name__ == "__main__":
    graph = load_graph()

    print("=== Gathering signals from 3 specialist agents ===\n")
    findings = gather_all_signals(graph)
    notes = apply_findings(graph, findings)

    if not notes:
        print("\nNo supply-chain risks found in recent news.")
    else:
        print("\n=== Direct signals (worst score per item) ===\n")
        for nid, entries in notes.items():
            worst = max(e[0] for e in entries)
            print(f"  [{worst:0.2f}] {graph[nid].label}")
            for sev, reason, agent in entries:
                print(f"        - ({agent}) {reason}")

        print("\n=== Risk score after propagation ===\n")
        results = [(nid, propagate(nid, graph)) for nid in graph]
        results.sort(key=lambda pair: pair[1], reverse=True)
        for nid, risk in results:
            bar = "#" * int(risk * 20)
            print(f"  {risk:0.2f}  {bar:<20}  {graph[nid].label}")