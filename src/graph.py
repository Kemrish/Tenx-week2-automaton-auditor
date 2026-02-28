#!/usr/bin/env python3
"""
Automaton Auditor - LangGraph Swarm for Autonomous Governance
"""

import asyncio
import uuid
from typing import TypedDict, Literal, Optional, List
from datetime import datetime
from pathlib import Path
import structlog
import logging
import sys
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START

from src.state import AgentState, ForensicEvidenceCollection
from src.nodes.detectives import DetectiveNodes
from src.nodes.judges import JudgeNodes
from src.nodes.justice import ChiefJusticeNode

# Load environment
load_dotenv()

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
structlog.configure(
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class AuditorGraph:
    """Main LangGraph definition for Automaton Auditor."""
    
    def __init__(self):
        self.checkpointer = MemorySaver()
        self.detectives = DetectiveNodes()
        self.judges = JudgeNodes()
        self.justice = ChiefJusticeNode()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Construct the StateGraph with all nodes and edges."""
        
        # Initialize graph with state schema
        builder = StateGraph(AgentState)
        
        # Add nodes
        builder.add_node("detective_dispatch", self._dispatch_detectives)
        builder.add_node("repo_investigator", self.detectives.repo_investigator)
        builder.add_node("doc_analyst", self.detectives.doc_analyst)
        builder.add_node("vision_inspector", self.detectives.vision_inspector)
        builder.add_node("evidence_aggregator", self._aggregate_evidence)
        builder.add_node("evidence_gate", self._evidence_gate)
        builder.add_node("judge_dispatch", self._dispatch_judges)
        builder.add_node("prosecutor", self.judges.prosecutor)
        builder.add_node("defense", self.judges.defense)
        builder.add_node("tech_lead", self.judges.tech_lead)
        builder.add_node("judge_aggregator", self._aggregate_judgments)
        builder.add_node("chief_justice", self.justice.synthesize)
        builder.add_node("report_generator", self._generate_output)
        
        # Define parallel detective execution
        builder.add_edge(START, "detective_dispatch")
        builder.add_edge("detective_dispatch", "repo_investigator")
        builder.add_edge("detective_dispatch", "doc_analyst")
        builder.add_edge("detective_dispatch", "vision_inspector")
        
        # Fan-in to aggregator
        builder.add_edge("repo_investigator", "evidence_aggregator")
        builder.add_edge("doc_analyst", "evidence_aggregator")
        builder.add_edge("vision_inspector", "evidence_aggregator")
        builder.add_edge("evidence_aggregator", "evidence_gate")
        
        # Conditional routing based on evidence
        builder.add_conditional_edges(
            "evidence_gate",
            self._route_based_on_evidence,
            {
                "proceed_to_judges": "judge_dispatch",
                "retry_detectives": "detective_dispatch",
                "abort": END
            }
        )
        
        # Parallel judicial execution
        builder.add_edge("judge_dispatch", "prosecutor")
        builder.add_edge("judge_dispatch", "defense")
        builder.add_edge("judge_dispatch", "tech_lead")
        
        # Fan-in to judge aggregator
        builder.add_edge("prosecutor", "judge_aggregator")
        builder.add_edge("defense", "judge_aggregator")
        builder.add_edge("tech_lead", "judge_aggregator")

        # Conditional routing based on judge output
        builder.add_conditional_edges(
            "judge_aggregator",
            self._route_based_on_judges,
            {
                "proceed_to_justice": "chief_justice",
                "retry_judges": "judge_dispatch",
            }
        )
        
        # Generate report
        builder.add_edge("chief_justice", "report_generator")
        builder.add_edge("report_generator", END)
        
        return builder.compile(checkpointer=self.checkpointer)
    
    async def _aggregate_evidence(self, state: AgentState) -> dict:
        """Aggregate evidence from all detectives."""
        
        logger.info("Aggregating evidence from detectives")
        
        # Merge evidence collections
        combined = ForensicEvidenceCollection()
        
        # This is simplified - in production would merge properly
        if 'evidences' in state:
            combined = state['evidences']
        
        return {
            'evidences': combined,
            'evidence_errors': state.get('evidence_errors', [])
        }

    def _evidence_gate(self, state: AgentState) -> dict:
        """Explicit gate to ensure all detectives have reported."""
        statuses = state.get('detective_status', {})
        updates = {}
        failed = [name for name, status in statuses.items() if status == 'failed']
        if failed:
            updates['evidence_errors'] = [f"Detective failed: {', '.join(sorted(failed))}"]
            updates['detective_attempts'] = state.get('detective_attempts', 0) + 1
        elif state.get('evidence_errors'):
            updates['detective_attempts'] = state.get('detective_attempts', 0) + 1
        return updates

    def _dispatch_detectives(self, state: AgentState) -> dict:
        """No-op node used to fan-out detective execution."""
        return {'evidence_errors': []}

    def _dispatch_judges(self, state: AgentState) -> dict:
        """No-op node used to fan-out judge execution."""
        return {'judge_errors': []}
    
    def _route_based_on_evidence(self, state: AgentState) -> Literal["proceed_to_judges", "retry_detectives", "abort"]:
        """Route based on evidence collection success."""
        
        errors = state.get('evidence_errors', [])
        attempts = state.get('detective_attempts', 0)
        
        if not state.get('repo_cloned', True):
            logger.error("Repository clone failed, aborting")
            return "abort"

        if len(errors) > 3:
            logger.error("Too many evidence errors", count=len(errors))
            return "abort"

        evidences = state.get('evidences')
        if evidences and (evidences.git is None or evidences.code is None):
            logger.warning("Missing core evidence, retrying detectives")
            return "retry_detectives"
        
        if errors:
            logger.warning("Evidence errors present, retrying", errors=errors)
            return "retry_detectives"
        
        return "proceed_to_judges"

    def _aggregate_judgments(self, state: AgentState) -> dict:
        """Aggregate judge errors for routing."""
        updates = {'judge_errors': state.get('judge_errors', [])}
        if updates['judge_errors']:
            updates['judge_attempts'] = state.get('judge_attempts', 0) + 1
            updates['warnings'] = [f"Judge output errors: {len(updates['judge_errors'])}"]
        return updates

    def _route_based_on_judges(self, state: AgentState) -> Literal["proceed_to_justice", "retry_judges"]:
        """Route based on judge output validity."""
        errors = state.get('judge_errors', [])
        attempts = state.get('judge_attempts', 0)
        if errors and attempts < 1:
            return "retry_judges"
        if errors:
            return "proceed_to_justice"
        return "proceed_to_justice"
    
    async def _generate_output(self, state: AgentState) -> dict:
        """Generate final output files."""
        
        if state.get('report_artifacts'):
            return {
                'report_path': state['report_artifacts'].get('full_report'),
                'report_artifacts': state['report_artifacts']
            }

        report = state.get('audit_report')
        if not report:
            return {}
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(f"audit/report_{timestamp}.md")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report.executive_summary)
            f.write("\n\n## Evidence Summary\n\n")
            f.write(f"- Git commits analyzed: {report.raw_evidence_summary.get('git_commits', 0)}\n")
            f.write(f"- Code analyzed: {report.raw_evidence_summary.get('code_analyzed', False)}\n")
            f.write(f"- PDF analyzed: {report.raw_evidence_summary.get('pdf_analyzed', False)}\n")
            f.write(f"- Diagrams analyzed: {report.raw_evidence_summary.get('diagrams_analyzed', 0)}\n")
            
            # Add criterion breakdown
            f.write("\n\n## Criterion Breakdown\n\n")
            for verdict in report.criterion_breakdown:
                f.write(f"### {verdict.criterion_id}\n")
                f.write(f"**Score:** {verdict.final_score}/5\n\n")
                if report.criterion_narratives.get(verdict.criterion_id):
                    f.write("**Narrative:**\n")
                    f.write(report.criterion_narratives[verdict.criterion_id] + "\n\n")
                f.write(f"**Dissent:** {verdict.dissent_summary}\n\n")
                f.write("**Remediation:**\n")
                for step in verdict.remediation_plan:
                    f.write(f"- {step}\n")
                f.write("\n")
            
            # Add remediation plan
            f.write("\n## Complete Remediation Plan\n\n")
            for criterion, steps in report.remediation_plan.items():
                f.write(f"### {criterion}\n")
                for step in steps:
                    f.write(f"- {step}\n")
                f.write("\n")
        
        logger.info(f"Report saved to {report_path}")
        
        return {'report_path': str(report_path)}
    
    async def run(self, repo_url: str, pdf_path: Optional[str] = None) -> dict:
        """Run the auditor on a single repository."""
        
        # Initialize state
        initial_state: AgentState = {
            'repo_url': repo_url,
            'pdf_path': pdf_path,
            'repo_cloned': False,
            'temp_dir': None,
            'evidences': ForensicEvidenceCollection(),
            'evidence_errors': [],
            'detective_status': {
                'repo_investigator': 'pending',
                'doc_analyst': 'pending',
                'vision_inspector': 'pending',
            },
            'detective_attempts': 0,
            'opinions': [],
            'criterion_judgments': {},
            'judge_errors': [],
            'judge_attempts': 0,
            'final_verdicts': [],
            'audit_report': None,
            'report_path': None,
            'report_artifacts': {},
            'trace_id': str(uuid.uuid4()),
            'errors': [],
            'warnings': []
        }
        
        # Run graph
        config = {
            "configurable": {
                "thread_id": f"audit_{uuid.uuid4()}",
                "trace_id": initial_state['trace_id']
            }
        }
        
        final_state = await self.graph.ainvoke(initial_state, config)
        
        return final_state
    
    async def batch_run(self, repo_urls: List[str], pdf_paths: Optional[List[str]] = None):
        """Run auditor on multiple repositories in parallel."""
        
        if pdf_paths and len(pdf_paths) != len(repo_urls):
            raise ValueError("Number of PDF paths must match number of repos")
        
        tasks = []
        for i, repo_url in enumerate(repo_urls):
            pdf_path = pdf_paths[i] if pdf_paths else None
            tasks.append(self.run(repo_url, pdf_path))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results


async def main():
    """Main entry point."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Automaton Auditor")
    parser.add_argument("--repo", help="GitHub repository URL")
    parser.add_argument("--pdf", help="PDF report path")
    parser.add_argument("--batch", nargs="+", help="Batch mode with multiple repo URLs")
    parser.add_argument("--pdfs", nargs="+", help="PDF paths for batch mode")
    
    args = parser.parse_args()
    
    auditor = AuditorGraph()
    
    if args.batch:
        results = await auditor.batch_run(args.batch, args.pdfs)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch item {i} failed", error=str(result))
            else:
                logger.info(f"Batch item {i} completed", 
                           repo=args.batch[i],
                           report=result.get('report_path'))
    
    elif args.repo:
        result = await auditor.run(args.repo, args.pdf)
        report_path = result.get('report_path')
        if not report_path and result.get('report_artifacts'):
            report_path = result['report_artifacts'].get('full_report')
        print(f"Audit complete. Report: {report_path}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
