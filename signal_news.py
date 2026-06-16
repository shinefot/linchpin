import json
from dotenv import load_dotenv
from anthropic import Anthropic

from graph import load_graph, propagate   # reuse the map + math we already built

load_dotenv()
client = Anthropic()


def gather_signals(graph):
    # Build a plain list of what's on our map, for Claude to watch out for.
    item_lines = [f"- {node.id}: {node.label}" for node in graph.values()]
    items_text = "\n".join(item_lines)

    prompt = f"""You are a supply-chain risk analyst. Below is a list of items we monitor, each shown as "id: name".

{items_text}

Search the web for RECENT news (roughly the last 6 months) about real supply disruptions affecting any of these items or the raw materials they depend on: shortages, export controls, factory outages, price spikes, or sanctions.

Then report ONLY what you actually found, as a JSON array. Each finding must use this exact shape:
[
  {{"node_id": "<one id from the list above>", "severity": <number between 0 and 1>, "reason": "<one short sentence>"}}
]

Severity guide: 0.2 = minor concern, 0.5 = moderate disruption, 0.8 = serious shortage, 1.0 = supply effectively halted.

Rules:
- Only include an item if you found credible recent news about it.
- If you found nothing, return an empty array: []
- Output the JSON array and NOTHING else.
"""

    print("Asking Claude to search the news... (this takes 10-30 seconds)\n")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
    )

    # The reply comes back in pieces; keep only the written-text pieces.
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    # Claude sometimes writes a sentence around the JSON, so grab just the part
    # between the first '[' and the last ']'.
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        print("No JSON found in the reply. Here's what came back:\n")
        print(text)
        return []

    return json.loads(text[start:end + 1])


if __name__ == "__main__":
    graph = load_graph()
    findings = gather_signals(graph)

    if not findings:
        print("No supply-chain risks found in recent news.")
    else:
        print(f"Claude found {len(findings)} signal(s):\n")
        for f in findings:
            node_id = f["node_id"]
            severity = f["severity"]
            if node_id in graph:
                graph[node_id].direct_risk = min(max(severity, 0.0), 1.0)
                print(f"  [{severity:0.2f}] {graph[node_id].label}: {f['reason']}")
            else:
                print(f"  (skipped unknown id '{node_id}')")

        # Run the SAME propagation engine from Phase 2.
        print("\nRisk score for each item after propagation:\n")
        results = [(nid, propagate(nid, graph)) for nid in graph]
        results.sort(key=lambda pair: pair[1], reverse=True)
        for node_id, risk in results:
            bar = "#" * int(risk * 20)
            print(f"  {risk:0.2f}  {bar:<20}  {graph[node_id].label}")