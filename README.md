# Automaton Auditor

A deep LangGraph swarm for autonomous governance: a digital courtroom that audits code repositories using forensic detectives, dialectical judges, and a supreme court synthesis engine.

## Overview

The Automaton Auditor implements a hierarchical multi-agent system:

- Detective Layer: Forensic sub-agents that collect objective evidence
  - RepoInvestigator: Git history and code structure analysis
  - DocAnalyst: PDF report analysis with cross-referencing
  - VisionInspector: Diagram analysis using multimodal LLMs
- Judicial Layer: Three persona-based judges that evaluate each criterion
  - Prosecutor: Hyper-critical, assumes "vibe coding"
  - Defense: Optimistic, rewards effort and intent
  - Tech Lead: Pragmatic, evaluates production readiness
- Supreme Court: Chief Justice synthesizes conflicting opinions into final verdict

## Installation

```bash
# Clone repository
git clone https://github.com/Kemrish/Tenx-week2-automaton-auditor.git
cd Tenx-week2-automaton-auditor

# Install uv (fast Python package installer)
pip install uv

# Install dependencies
uv pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Run

```bash
# Single repo audit
python -m src.graph --repo https://github.com/your-org/your-repo.git

# Repo + PDF report
python -m src.graph --repo https://github.com/your-org/your-repo.git --pdf path/to/report.pdf

# Batch mode
python -m src.graph --batch https://github.com/org/repo1.git https://github.com/org/repo2.git
```

Reports are saved to `audit/` as three artifacts:
- Full narrative report (`report_YYYYMMDD_HHMMSS_full.md`)
- Executive summary (`report_YYYYMMDD_HHMMSS_summary.md`)
- Machine-readable JSON (`report_YYYYMMDD_HHMMSS.json`)

## Project Structure

- `src/graph.py`: LangGraph orchestration (fan-out/fan-in, conditional routing)
- `src/nodes/`: Detective, judge, and chief justice nodes
- `src/tools/`: Git, AST, PDF, and vision forensic tooling
- `rubric/`: Evaluation rubric
- `audit/`: Generated reports
- `ARCHITECTURE_NOTES.md`: System architecture and flow diagram

## Notes

- Dependency lock file: `uv.lock` (commit for reproducible installs).
- Use `.env.example` as the canonical list of required environment variables.
