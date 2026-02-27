from typing import Dict, Any, List
import os
import asyncio
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import structlog

from ..state import (
    AgentState,
    JudicialOpinion,
    CriterionJudgment,
    ForensicEvidenceCollection
)
from ..utils.rubric_loader import RubricLoader

logger = structlog.get_logger()


class JudgeNodes:
    """Judicial nodes with distinct personas."""
    
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        api_key = (
            os.getenv("OPENROUTER_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        base_url = os.getenv("OPENROUTER_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL")
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.2,
            api_key=api_key,
            base_url=base_url,
        )
        self.rubric = RubricLoader.load_rubric()
        
        # Output parser
        self.parser = PydanticOutputParser(pydantic_object=JudicialOpinion)
        self.format_instructions = self.parser.get_format_instructions()

        # Persona prompts
        self.prosecutor_prompt = self._create_prosecutor_prompt()
        self.defense_prompt = self._create_defense_prompt()
        self.tech_lead_prompt = self._create_tech_lead_prompt()
    
    def _create_prosecutor_prompt(self) -> ChatPromptTemplate:
        """Create strict, critical prosecutor persona."""
        
        return ChatPromptTemplate.from_messages([
            ("system", """You are the PROSECUTOR in a digital courtroom. Your role is to be hyper-critical and assume "vibe coding" - that the defendant cut corners.

Core Philosophy: "Trust No One. Assume Vibe Coding."

You must scrutinize evidence for gaps, security flaws, and laziness. For each rubric criterion:

1. If the evidence shows missing artifacts, charge with "Vaporware"
2. If security measures are bypassed, charge with "Security Theater"
3. If code exists but isn't integrated, charge with "Orphaned Code"
4. If commits are vague, charge with "Lazy Checkpointing"

Scoring Guidelines:
- Score 0-1: Critical failures, security flaws, missing core components
- Score 2-3: Present but flawed implementation
- Score 4-5: Only assign if evidence is irrefutable and production-grade

Rubric: {rubric}

Evidence: {evidence}

For criterion: {criterion_id}

Return ONLY valid JSON that matches the schema below.
{format_instructions}
"""),
            ("human", "Render your verdict for {criterion_name} based on the forensic evidence.")
        ])
    
    def _create_defense_prompt(self) -> ChatPromptTemplate:
        """Create optimistic defense attorney persona."""
        
        return ChatPromptTemplate.from_messages([
            ("system", """You are the DEFENSE ATTORNEY in a digital courtroom. Your role is to look for effort, intent, and creative workarounds.

Core Philosophy: "Reward Effort and Intent. Look for the 'Spirit of the Law'."

You must highlight:
1. Creative solutions even if imperfect
2. Deep understanding shown in architecture notes
3. Effort demonstrated in git history (iteration, struggle)
4. Theoretical alignment with concepts like Cognitive Debt

Scoring Guidelines:
- Be generous - if they tried, they get points
- Give partial credit for partial implementations
- Boost scores for good documentation even if code is buggy
- Consider git narrative of learning and iteration

Rubric: {rubric}

Evidence: {evidence}

For criterion: {criterion_id}

Return ONLY valid JSON that matches the schema below.
{format_instructions}
"""),
            ("human", "Defend this submission for {criterion_name}.")
        ])
    
    def _create_tech_lead_prompt(self) -> ChatPromptTemplate:
        """Create pragmatic tech lead persona."""
        
        return ChatPromptTemplate.from_messages([
            ("system", """You are the TECH LEAD in a digital courtroom. Your role is to be pragmatic - does it actually work? Is it maintainable?

Core Philosophy: "Does it actually work? Is it maintainable?"

You must evaluate:
1. Architectural soundness - is the pattern isolated and correct?
2. Code cleanliness - is it production-ready?
3. Practical viability - would this pass code review?
4. Technical debt - how much cleanup is needed?

You are the tie-breaker between Prosecutor and Defense:
- If Prosecutor shows fatal security flaw, side with them
- If Defense shows genuine innovation, side with them
- Otherwise, find the pragmatic middle ground

Scoring Guidelines:
- Score 1: Unworkable, dangerous, or incomprehensible
- Score 3: Works but needs refactoring - acceptable
- Score 5: Production-grade, clean, well-architected

Rubric: {rubric}

Evidence: {evidence}

For criterion: {criterion_id}

Return ONLY valid JSON that matches the schema below.
{format_instructions}
"""),
            ("human", "Assess {criterion_name} for production readiness.")
        ])
    
    async def prosecutor(self, state: AgentState) -> Dict[str, Any]:
        """Prosecutor node - harsh critic."""
        return await self._judge_criteria(state, "Prosecutor", self.prosecutor_prompt)
    
    async def defense(self, state: AgentState) -> Dict[str, Any]:
        """Defense node - optimistic advocate."""
        return await self._judge_criteria(state, "Defense", self.defense_prompt)
    
    async def tech_lead(self, state: AgentState) -> Dict[str, Any]:
        """Tech lead node - pragmatic evaluator."""
        return await self._judge_criteria(state, "TechLead", self.tech_lead_prompt)
    
    async def _judge_criteria(self, state: AgentState, persona: str, 
                              prompt_template: ChatPromptTemplate) -> Dict[str, Any]:
        """Judge all criteria for a specific persona."""
        
        opinions = []
        
        # Get evidence summary
        evidence_summary = self._summarize_evidence(state['evidences'])
        
        # Judge each criterion
        for criterion in self.rubric['dimensions']:
            try:
                # Build chain
                chain = prompt_template | self.llm | self.parser
                
                # Invoke
                result = await chain.ainvoke({
                    'rubric': json.dumps(self.rubric, indent=2),
                    'evidence': evidence_summary,
                    'criterion_id': criterion['id'],
                    'criterion_name': criterion['name'],
                    'format_instructions': self.format_instructions
                })
                
                # Ensure correct persona
                result.judge = persona
                result.criterion_id = criterion['id']
                
                opinions.append(result)
                
            except Exception as e:
                logger.error(f"Judgment failed for {criterion['id']}", 
                           persona=persona, error=str(e))
                
                # Create fallback opinion
                opinions.append(JudicialOpinion(
                    judge=persona,
                    criterion_id=criterion['id'],
                    score=1,
                    argument=f"Judgment failed: {str(e)}",
                    cited_evidence=[],
                    confidence=0.1
                ))
        
        # Group by criterion
        criterion_judgments = {}
        for opinion in opinions:
            if opinion.criterion_id not in criterion_judgments:
                criterion_judgments[opinion.criterion_id] = CriterionJudgment(
                    criterion_id=opinion.criterion_id,
                    criterion_name=next(
                        (c['name'] for c in self.rubric['dimensions'] 
                         if c['id'] == opinion.criterion_id),
                        'Unknown'
                    ),
                    opinions=[]
                )
            criterion_judgments[opinion.criterion_id].opinions.append(opinion)
        
        return {
            'opinions': opinions,
            'criterion_judgments': criterion_judgments
        }
    
    def _summarize_evidence(self, evidences: ForensicEvidenceCollection) -> str:
        """Create a summary of forensic evidence for judges."""
        
        summary_parts = []
        
        if evidences.git:
            summary_parts.append(f"Git History: {evidences.git.commit_count} commits")
            summary_parts.append(f"Progression: {evidences.git.progression_pattern}")
            summary_parts.append(f"Atomic: {evidences.git.has_atomic_history}")
        
        if evidences.code:
            summary_parts.append(f"Architecture Notes: {evidences.code.architecture_notes_exists}")
            summary_parts.append(f"Tool Registered: {evidences.code.tool_registered}")
            summary_parts.append(f"Middleware: {evidences.code.middleware_exists}")
            summary_parts.append(f"Hashing: {evidences.code.hashing_implemented}")
            summary_parts.append(f"Trace Writing: {evidences.code.trace_writing_implemented}")
            summary_parts.append(f"State Models: {evidences.code.state_models_detected}")
            summary_parts.append(
                f"Graph Structure: fan_out={evidences.code.graph_fan_out_detected}, "
                f"fan_in={evidences.code.graph_fan_in_detected}, "
                f"conditional={evidences.code.conditional_edges_detected}, "
                f"checkpointer={evidences.code.checkpointer_detected}, "
                f"nodes={evidences.code.graph_node_count}, edges={evidences.code.graph_edge_count}"
            )
        
        if evidences.pdf:
            summary_parts.append(f"PDF Mentions: {len(evidences.pdf.claimed_file_paths)} paths")
            summary_parts.append(f"Hallucinated: {len(evidences.pdf.hallucinated_paths)}")
            if evidences.pdf.retrieval_snippets:
                summary_parts.append(
                    "PDF Retrieval: " + ", ".join(sorted(evidences.pdf.retrieval_snippets.keys()))
                )
        
        if evidences.images:
            summary_parts.append(f"Diagrams: {evidences.images.image_count}")
            summary_parts.append(f"Types: {', '.join(evidences.images.diagram_types)}")
        
        return "\n".join(summary_parts)
