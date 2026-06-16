# Linchpin

An early-warning monitor for supply-chain chokepoints. Linchpin reads live news with a team of AI agents, maps how a disruption to one raw material ripples downstream, and writes a short risk briefing — for any supply chain you can describe.

It ships with a semiconductor (EUV lithography) example. Point it at a different supply chain by editing a single file.

## How it works

Linchpin runs a small pipeline:

1. Three **signal agents** (news, regulatory, materials) each search the live web for recent disruptions and return structured findings.
2. Their findings are merged onto a **dependency graph** — a map of which item needs what.
3. A **propagation step** traces each disruption downstream, so a shock to a raw material raises the risk on the finished products that depend on it. Single-source items (no backup supplier) amplify that risk.
4. An **analyst** (plain code) assembles the evidence and traces each risk back to its root cause.
5. A **briefing writer** (one model call) turns that evidence into a readable report, saved to `reports/`.

The dependency map lives in `data/dependency_graph.yaml`. That file is the core of the project — the code is generic; the map is the knowledge.

## Quick start

Requires Python 3.10+ and an Anthropic API key.

    # 1. Clone and enter the project
    git clone https://github.com/<your-username>/linchpin.git
    cd linchpin

    # 2. Create and activate a virtual environment (Windows)
    python -m venv venv
    .\venv\Scripts\Activate.ps1

    # 3. Install dependencies
    pip install -r requirements.txt

    # 4. Add your API key: create a file named .env containing
    #    ANTHROPIC_API_KEY=sk-ant-your-key-here

    # 5. Run the full monitor
    python briefing.py

Web search must be enabled for your Anthropic account (Console settings).

## Project structure

    linchpin/
    ├── data/
    │   └── dependency_graph.yaml   the supply-chain map (the core data)
    ├── graph.py                    loads the map + risk propagation engine
    ├── signals.py                  three signal agents + merge logic
    ├── briefing.py                 analyst + briefing writer (run this one)
    └── requirements.txt

## Pointing it at another supply chain

Edit `data/dependency_graph.yaml`. Describe each item with an `id`, a `label`, what it `depends_on`, and whether it's `single_source`. No code changes needed — the agents, propagation, and briefing all work off whatever map you provide.

## Status and honest limitations

This is a working **prototype**, not a production tool:

- The dependency map is small and hand-built. A missing or wrong link will silently skew results.
- The risk scores are a **demonstrative heuristic**, not a validated model.
- Output quality depends entirely on the accuracy of the map and the live news available.

It exists to show the architecture working end to end, and to be forked toward other supply chains.