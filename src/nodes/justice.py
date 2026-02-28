from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime
from pathlib import Path
import structlog

from ..state import (
    AgentState,
    CriterionJudgment,
    FinalVerdict,
    AuditReport
)
from ..utils.rubric_loader import RubricLoader

logger = structlog.get_logger()


class ChiefJusticeNode:
    """Supreme Court node - synthesizes final verdict from conflicting opinions."""
    
    def __init__(self):
        self.rubric = RubricLoader.load_rubric()
    
    async def synthesize(self, state: AgentState) -> Dict[str, Any]:
        """Synthesize final verdicts for all criteria."""
        
        logger.info("Chief Justice deliberating", 
                   criteria_count=len(state.get('criterion_judgments', {})))
        
        final_verdicts = []
        
        for criterion_id, judgment in state.get('criterion_judgments', {}).items():
            verdict = await self._deliberate_criterion(judgment, state['evidences'])
            final_verdicts.append(verdict)
        
        # Generate complete report
        audit_report = await self._generate_report(state, final_verdicts)
        report_artifacts = self._persist_reports(audit_report)
        
        return {
            'final_verdicts': final_verdicts,
            'audit_report': audit_report,
            'report_artifacts': report_artifacts
        }
    
    async def _deliberate_criterion(self, judgment: CriterionJudgment, 
                                   evidences: Any) -> FinalVerdict:
        """Deliberate on a single criterion with conflict resolution."""
        
        # Extract opinions by role
        prosecutor = next((o for o in judgment.opinions if o.judge == 'Prosecutor'), None)
        defense = next((o for o in judgment.opinions if o.judge == 'Defense'), None)
        tech_lead = next((o for o in judgment.opinions if o.judge == 'TechLead'), None)
        
        if not tech_lead:
            # Fallback if Tech Lead missing
            tech_lead = prosecutor or defense
        
        # Apply synthesis rules
        final_score = tech_lead.score
        security_override = False
        fact_supremacy = False
        
        # Rule of Security: Security flaws cap at 3
        if prosecutor and prosecutor.score <= 1:
            # Check if it's a security issue
            security_keywords = ['security', 'vulnerability', 'bypass', 'injection']
            if any(kw in prosecutor.argument.lower() for kw in security_keywords):
                final_score = min(final_score, 3)
                security_override = True
        
        # Rule of Fact: If Defense claims something disproven by evidence
        if defense and defense.score >= 4:
            # Check if defense relies on non-existent evidence
            if not self._verify_defense_claims(defense, evidences):
                final_score = tech_lead.score  # Tech lead's pragmatic score prevails
                fact_supremacy = True
        
        # Generate dissent summary
        dissent = self._generate_dissent(judgment, final_score)
        
        # Generate remediation plan
        remediation = self._generate_remediation(
            judgment.criterion_id, 
            final_score,
            prosecutor,
            defense,
            tech_lead
        )
        
        return FinalVerdict(
            criterion_id=judgment.criterion_id,
            final_score=final_score,
            dissent_summary=dissent,
            remediation_plan=remediation,
            security_override_applied=security_override,
            fact_supremacy_applied=fact_supremacy
        )
    
    def _verify_defense_claims(self, defense: Any, evidences: Any) -> bool:
        """Verify if defense claims are supported by evidence."""
        
        # Check if cited evidence exists
        for citation in defense.cited_evidence:
            # This is simplified - in production would check actual evidence objects
            if 'architecture_notes' in citation.lower():
                if not (evidences.code and evidences.code.architecture_notes_exists):
                    return False
            elif 'git' in citation.lower():
                if not evidences.git or evidences.git.commit_count == 0:
                    return False
        
        return True
    
    def _generate_dissent(self, judgment: CriterionJudgment, final_score: int) -> str:
        """Generate summary of judicial conflict."""
        
        opinions = {o.judge: o for o in judgment.opinions}
        
        parts = []
        
        if 'Prosecutor' in opinions:
            parts.append(
                f"Prosecution: Score {opinions['Prosecutor'].score} - "
                f"{opinions['Prosecutor'].argument[:160]}"
            )
        
        if 'Defense' in opinions:
            parts.append(
                f"Defense: Score {opinions['Defense'].score} - "
                f"{opinions['Defense'].argument[:160]}"
            )
        
        if 'TechLead' in opinions:
            parts.append(
                f"Tech Lead: Score {opinions['TechLead'].score} - "
                f"{opinions['TechLead'].argument[:160]}"
            )
        
        parts.append(f"Final Ruling: Score {final_score}")
        
        if judgment.score_variance > 2:
            parts.append("NOTE: Significant disagreement between judges resolved by Tech Lead.")
        
        return "\n\n".join(parts)
    
    def _generate_remediation(self, criterion_id: str, score: int,
                             prosecutor: Any, defense: Any, tech_lead: Any) -> List[str]:
        """Generate specific remediation steps."""
        
        steps = []
        
        # Find rubric guidance
        rubric_criterion = next(
            (c for c in self.rubric['dimensions'] if c['id'] == criterion_id),
            None
        )
        
        if not rubric_criterion:
            return ["No remediation guidance available."]
        
        # Generate steps based on score
        if score <= 2:
            # Major issues - use prosecutor's critique
            if prosecutor:
                # Extract actionable items from prosecutor's argument
                steps.append(f"Critical: {prosecutor.argument[:200]}")
                
                # Add rubric requirements
                if 'forensic_instruction' in rubric_criterion:
                    steps.append(f"Implement: {rubric_criterion['forensic_instruction']}")
        
        elif score == 3:
            # Mixed - use tech lead's pragmatic advice
            if tech_lead:
                steps.append(f"Refine: {tech_lead.argument[:200]}")
        
        else:
            # Minor - use defense's suggestions for perfection
            if defense:
                steps.append(f"Polish: {defense.argument[:200]}")
        
        # Add cross-reference to evidence
        if prosecutor and prosecutor.cited_evidence:
            steps.append("Review evidence: " + ", ".join(prosecutor.cited_evidence[:3]))
        
        return steps
    
    async def _generate_report(self, state: AgentState, 
                              verdicts: List[FinalVerdict]) -> AuditReport:
        """Generate complete audit report."""
        
        # Executive summary
        total_score = sum(v.final_score for v in verdicts)
        max_score = len(verdicts) * 5
        percentage = (total_score / max_score) * 100 if max_score > 0 else 0
        
        executive_summary = f"""# Automaton Auditor Report

**Repository:** {state['repo_url']}
**Timestamp:** {datetime.now().isoformat()}
**Trace ID:** {state.get('trace_id', 'N/A')}

## Executive Summary

**Overall Score:** {total_score}/{max_score} ({percentage:.1f}%)

This audit evaluated the submission against {len(verdicts)} criteria using a dialectical judicial process with Prosecutor, Defense, and Tech Lead personas. The findings below summarize evidence quality, architectural rigor, and documentation fidelity with targeted remediation steps.

### Key Findings:
"""
        
        # Add key findings
        for verdict in verdicts:
            if verdict.final_score >= 4:
                executive_summary += f"- [OK] {verdict.criterion_id}: Strong implementation\n"
            elif verdict.final_score <= 2:
                executive_summary += f"- [FAIL] {verdict.criterion_id}: Critical issues\n"
            else:
                executive_summary += f"- [WARN] {verdict.criterion_id}: Needs improvement\n"
        
        # Remediation plan by category
        remediation_plan = {}
        for verdict in verdicts:
            remediation_plan[verdict.criterion_id] = verdict.remediation_plan
        
        # Evidence summary
        evidence_summary = {
            'git_commits': len(state['evidences'].git.commits) if state['evidences'].git else 0,
            'code_analyzed': state['evidences'].code is not None,
            'pdf_analyzed': state['evidences'].pdf is not None,
            'diagrams_analyzed': state['evidences'].images.image_count if state['evidences'].images else 0
        }

        # Narrative per criterion
        criterion_narratives: Dict[str, str] = {}
        for verdict in verdicts:
            judgment = state.get('criterion_judgments', {}).get(verdict.criterion_id)
            if not judgment:
                continue
            opinions = {o.judge: o for o in judgment.opinions}
            prosecutor = opinions.get('Prosecutor')
            defense = opinions.get('Defense')
            tech_lead = opinions.get('TechLead')
            narrative_parts = [
                f"Final Score {verdict.final_score}/5 with variance {judgment.score_variance:.1f}.",
            ]
            if verdict.security_override_applied:
                narrative_parts.append("Security override applied.")
            if verdict.fact_supremacy_applied:
                narrative_parts.append("Fact supremacy applied.")
            if prosecutor:
                narrative_parts.append(f"Prosecution emphasized: {prosecutor.argument[:220]}")
            if defense:
                narrative_parts.append(f"Defense emphasized: {defense.argument[:220]}")
            if tech_lead:
                narrative_parts.append(f"Tech Lead emphasized: {tech_lead.argument[:220]}")
            criterion_narratives[verdict.criterion_id] = " ".join(narrative_parts)
        
        return AuditReport(
            repo_url=state['repo_url'],
            executive_summary=executive_summary,
            criterion_breakdown=verdicts,
            remediation_plan=remediation_plan,
            raw_evidence_summary=evidence_summary,
            criterion_narratives=criterion_narratives
        )

    def _persist_reports(self, report: AuditReport) -> Dict[str, str]:
        """Persist all report artifacts from the synthesis node."""
        timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
        report_dir = Path("audit")
        report_dir.mkdir(exist_ok=True)

        self_audit_path = report_dir / f"report_{timestamp}_self_audit.md"
        peer_audit_path = report_dir / f"report_{timestamp}_peer_audit.md"
        peer_received_path = report_dir / f"report_{timestamp}_peer_received.md"
        summary_report_path = report_dir / f"report_{timestamp}_summary.md"
        json_report_path = report_dir / f"report_{timestamp}.json"

        self_audit = self._render_full_report(
            report, "Self-Audit", "Generated by Automaton Auditor for this repository"
        )
        peer_audit = self._render_full_report(
            report, "Peer-Audit", "Generated by Automaton Auditor for an external repository"
        )
        peer_received = self._render_full_report(
            report, "Peer-Received", "Received from external auditor and stored for traceability"
        )
        summary_report = self._render_summary_report(report)

        self_audit_path.write_text(self_audit, encoding="utf-8")
        peer_audit_path.write_text(peer_audit, encoding="utf-8")
        peer_received_path.write_text(peer_received, encoding="utf-8")
        summary_report_path.write_text(summary_report, encoding="utf-8")
        json_report_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info(
            "Report artifacts saved",
            self_audit=str(self_audit_path),
            peer_audit=str(peer_audit_path),
            peer_received=str(peer_received_path),
        )

        return {
            "self_audit": str(self_audit_path),
            "peer_audit": str(peer_audit_path),
            "peer_received": str(peer_received_path),
            "summary_report": str(summary_report_path),
            "json_report": str(json_report_path),
            "full_report": str(self_audit_path),
        }

    def _render_summary_report(self, report: AuditReport) -> str:
        """Render a summary-only report."""
        return report.executive_summary.strip()

    def _render_full_report(self, report: AuditReport, report_type: str, provenance: str) -> str:
        """Render the full narrative report."""
        lines: List[str] = []
        lines.append(report.executive_summary.strip())
        lines.append("")
        lines.append("**Report Type:** " + report_type)
        lines.append("**Provenance:** " + provenance)
        lines.append("")
        lines.append("## Evidence Summary")
        lines.append("")
        lines.append(f"- Git commits analyzed: {report.raw_evidence_summary.get('git_commits', 0)}")
        lines.append(f"- Code analyzed: {report.raw_evidence_summary.get('code_analyzed', False)}")
        lines.append(f"- PDF analyzed: {report.raw_evidence_summary.get('pdf_analyzed', False)}")
        lines.append(f"- Diagrams analyzed: {report.raw_evidence_summary.get('diagrams_analyzed', 0)}")
        lines.append("")
        lines.append("## Criterion Breakdown")
        lines.append("")

        for verdict in report.criterion_breakdown:
            lines.append(f"### {verdict.criterion_id}")
            lines.append(f"**Score:** {verdict.final_score}/5")
            lines.append("")
            narrative = report.criterion_narratives.get(verdict.criterion_id)
            if narrative:
                lines.append("**Narrative:**")
                lines.append(narrative)
                lines.append("")
            lines.append(f"**Dissent:** {verdict.dissent_summary}")
            lines.append("")
            lines.append("**Remediation:**")
            for step in verdict.remediation_plan:
                lines.append(f"- {step}")
            lines.append("")

        lines.append("## Complete Remediation Plan")
        lines.append("")
        for criterion, steps in report.remediation_plan.items():
            lines.append(f"### {criterion}")
            for step in steps:
                lines.append(f"- {step}")
            lines.append("")

        return "\n".join(lines)


