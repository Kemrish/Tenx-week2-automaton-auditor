# Automaton Auditor

A deep LangGraph swarm for autonomous governance - a digital courtroom that audits code repositories using forensic detectives, dialectical judges, and a supreme court synthesis engine.

## Overview

The Automaton Auditor implements a hierarchical multi-agent system:

- **Detective Layer**: Forensic sub-agents that collect objective evidence
  - RepoInvestigator: Git history and code structure analysis
  - DocAnalyst: PDF report analysis with cross-referencing
  - VisionInspector: Diagram analysis using multimodal LLMs

- **Judicial Layer**: Three persona-based judges that evaluate each criterion
  - Prosecutor: Hyper-critical, assumes "vibe coding"
  - Defense: Optimistic, rewards effort and intent
  - Tech Lead: Pragmatic, evaluates production readiness

- **Supreme Court**: Chief Justice synthesizes conflicting opinions into final verdict

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