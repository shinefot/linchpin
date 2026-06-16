import os
import datetime
from dotenv import load_dotenv
from anthropic import Anthropic

from graph import load_graph, propagate
from signals import gather_all_signals, apply_findings

load_dotenv()
client = Anthropic()


def trace_cause(node_id, graph):
    """Follow the chain from an item DOWN to the upstream driver of its risk."""
    path = [node_id]
    current = graph[node_id]
    seen = {node_id}
    while current.depends_on:
        # of the things this item needs, which carries the most risk?
        worst_dep = max(current.depends_on, key=lambda d: propagate(d, graph))
        if propagate(worst_dep, graph) <= 0 or worst_dep in seen:
            break
        path.append(worst_dep)
        seen.add(worst_dep)
        current = graph[worst_dep]
    return path


def build_evidence(graph, notes):
    """The ANALYST (pure code): assemble a clear evidence summary from the
    propagated scores, the cause chains, and the reasons each agent gave."""
    ranked = sorted(graph.values(), key=lambda n: propagate(n.id, graph), reverse=True)

    lines = []
    for node in ranked:
        score = propagate(node.id, graph)
        if score <= 0:
            continue
        chain = trace_cause(node.id, graph)
        chain_labels = " <- ".join(graph[c].label for c in chain)
        lines.append(f"ITEM: {node.label}  (risk {score:0.2f})")
        lines.append(f"  cause chain: {chain_labels}")
        for c in chain:                       # reasons found anywhere along the chain
            for sev, reason, agent in notes.get(c, []):
                lines.append(f"  reason ({graph[c].label}, {sev:0.2f}): {reason}")
        lines.append("")
    return "\n".join(lines)


def write_briefing(evidence):
    """The BRIEFING WRITER (one Claude call): turn evidence into a readable report."""
    prompt = f"""You are a supply-chain risk briefing writer. Below is analyzed evidence about a semiconductor supply chain, already scored and traced.

{evidence}

Write a short briefing in markdown for a busy, non-expert reader. Include:
1. A one-line headline summarizing the overall situation.
2. "Top concern": the single highest risk, explaining the cause chain in plain language (e.g. how an upstream material problem reaches a finished machine).
3. "Other risks": a short bullet list of the remaining concerns, one line each.

Rules: base everything ONLY on the evidence above. Do not invent numbers or events. Keep it under 250 words. Be clear and calm, not alarmist."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in response.content if b.type == "text")


if __name__ == "__main__":
    graph = load_graph()

    print("=== Step 1/3: gathering signals (3 agents, ~1 minute) ===\n")
    findings = gather_all_signals(graph)
    notes = apply_findings(graph, findings)

    if not notes:
        print("\nNo risks found in recent news. Nothing to brief.")
    else:
        print("\n=== Step 2/3: analyst assembling the evidence ===")
        evidence = build_evidence(graph, notes)

        print("\n=== Step 3/3: briefing writer drafting the report ===\n")
        briefing = write_briefing(evidence)
        print(briefing)

        os.makedirs("reports", exist_ok=True)   # make a reports folder if needed
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"reports/briefing_{stamp}.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(briefing)
        print(f"\n\nSaved to {path}")