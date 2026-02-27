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
        builder.add_node("prosecutor", self.judges.prosecutor)
        builder.add_node("defense", self.judges.defense)
        builder.add_node("tech_lead", self.judges.tech_lead)
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
        
        # Conditional routing based on evidence
        builder.add_conditional_edges(
            "evidence_aggregator",
            self._route_based_on_evidence,
            {
                "proceed_to_judges": "prosecutor",  # Also goes to defense/tech_lead via parallel
                "retry_detectives": "detective_dispatch",
                "abort": END
            }
        )
        
        # Parallel judicial execution
        builder.add_edge("evidence_aggregator", "prosecutor")
        builder.add_edge("evidence_aggregator", "defense")
        builder.add_edge("evidence_aggregator", "tech_lead")
        
        # Fan-in to chief justice
        builder.add_edge("prosecutor", "chief_justice")
        builder.add_edge("defense", "chief_justice")
        builder.add_edge("tech_lead", "chief_justice")
        
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

    def _dispatch_detectives(self, state: AgentState) -> dict:
        """No-op node used to fan-out detective execution."""
        return {}
    
    def _route_based_on_evidence(self, state: AgentState) -> Literal["proceed_to_judges", "retry_detectives", "abort"]:
        """Route based on evidence collection success."""
        
        errors = state.get('evidence_errors', [])
        
        if len(errors) > 3:
            logger.error("Too many evidence errors", count=len(errors))
            return "abort"
        
        if errors:
            logger.warning("Evidence errors present, retrying", errors=errors)
            return "retry_detectives"
        
        return "proceed_to_judges"
    
    async def _generate_output(self, state: AgentState) -> dict:
        """Generate final output files."""
        
        report = state.get('audit_report')
        if not report:
            return {}
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(f"audit/report_{timestamp}.md")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report.executive_summary)
            
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
            'opinions': [],
            'criterion_judgments': {},
            'final_verdicts': [],
            'audit_report': None,
            'report_path': None,
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
        print(f"Audit complete. Report: {result.get('report_path')}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
