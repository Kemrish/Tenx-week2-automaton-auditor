import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
import structlog

from ..state import (
    AgentState, 
    ForensicEvidenceCollection,
    GitForensicEvidence,
    CodeStructureEvidence,
    PdfForensicEvidence,
    ImageForensicEvidence,
    Evidence
)
from ..tools.git_tools import GitForensicTool
from ..tools.ast_tools import ASTForensicTool
from ..tools.pdf_tools import PDFForensicTool
from ..tools.vision_tools import VisionForensicTool
from ..utils.sandbox import SandboxEnvironment

logger = structlog.get_logger()


class DetectiveNodes:
    """Forensic detective nodes for evidence collection."""
    
    def __init__(self):
        self.git_tool = GitForensicTool()
        self.ast_tool = ASTForensicTool()
        self.pdf_tool = PDFForensicTool()
        self.vision_tool = VisionForensicTool()
        self.sandbox = SandboxEnvironment()
    
    async def repo_investigator(self, state: AgentState) -> Dict[str, Any]:
        """Code detective node - analyzes git and code structure."""
        
        logger.info("Starting repo investigation", repo_url=state['repo_url'])
        
        try:
            # Clone repository in sandbox
            async with self.sandbox() as sandbox:
                repo_path = await self.git_tool.clone_repository(state['repo_url'])
                
                # Run parallel analyses
                git_analysis, code_analysis = await asyncio.gather(
                    self.git_tool.analyze_git_history(),
                    self.ast_tool.analyze_codebase(repo_path)
                )
                
                # Clean up
                self.git_tool.cleanup()
            
            # Create evidence objects
            git_evidence = GitForensicEvidence(
                commits=git_analysis.commits,
                commit_count=git_analysis.commit_count,
                has_atomic_history=git_analysis.has_atomic_history,
                progression_pattern=git_analysis.progression_pattern,
                timestamps=git_analysis.timestamps
            )
            
            code_evidence = CodeStructureEvidence(
                architecture_notes_exists=code_analysis['architecture_notes']['exists'],
                architecture_notes_paths=code_analysis['architecture_notes'].get('paths', []),
                tool_registered=code_analysis['tool_registration']['found'],
                tool_location=code_analysis['tool_registration']['locations'][0] if code_analysis['tool_registration']['locations'] else None,
                system_prompt_contains_instruction=code_analysis['system_prompt']['found'],
                system_prompt_location=code_analysis['system_prompt']['locations'][0] if code_analysis['system_prompt']['locations'] else None,
                middleware_exists=code_analysis['middleware']['found'],
                middleware_location=code_analysis['middleware']['locations'][0] if code_analysis['middleware']['locations'] else None,
                hashing_implemented=code_analysis['hashing']['found'],
                hashing_location=code_analysis['hashing']['locations'][0] if code_analysis['hashing']['locations'] else None,
                trace_writing_implemented=code_analysis['trace_writing']['found'],
                trace_location=code_analysis['trace_writing']['locations'][0] if code_analysis['trace_writing']['locations'] else None,
                state_models_detected=code_analysis['state_models']['found'],
                state_model_locations=code_analysis['state_models']['locations'],
                graph_fan_out_detected=code_analysis['graph_structure']['fan_out'],
                graph_fan_in_detected=code_analysis['graph_structure']['fan_in'],
                conditional_edges_detected=code_analysis['graph_structure']['conditional_edges'],
                checkpointer_detected=code_analysis['graph_structure']['checkpointer_used'],
                graph_edge_count=code_analysis['graph_structure']['edge_count'],
                graph_node_count=code_analysis['graph_structure']['node_count'],
            )
            
            # Update state
            new_evidences = ForensicEvidenceCollection(
                git=git_evidence,
                code=code_evidence,
                raw_evidence={
                    'git_commits': Evidence(
                        found=True,
                        content=str([c.message for c in git_analysis.commits]),
                        location='git_log',
                        rationale="Commit messages used to infer history quality and progression.",
                        confidence=1.0
                    ),
                    'graph_structure': Evidence(
                        found=True,
                        content=str(code_analysis.get('graph_structure', {})),
                        location='static_analysis',
                        rationale="Static analysis of StateGraph construction to confirm fan-out/fan-in/conditional edges.",
                        confidence=0.9
                    ),
                    'state_models': Evidence(
                        found=code_analysis['state_models']['found'],
                        content=str(code_analysis['state_models']),
                        location='static_analysis',
                        rationale="Pydantic model presence indicates typed state and validation.",
                        confidence=0.9 if code_analysis['state_models']['found'] else 0.6
                    )
                }
            )
            
            return {
                'evidences': new_evidences,
                'repo_cloned': True,
                'temp_dir': str(repo_path) if repo_path else None,
                'detective_status': {'repo_investigator': 'done'}
            }
            
        except Exception as e:
            logger.error("Repo investigation failed", error=str(e))
            return {
                'evidence_errors': [f"Repo investigation failed: {str(e)}"],
                'repo_cloned': False,
                'detective_status': {'repo_investigator': 'failed'}
            }
    
    async def doc_analyst(self, state: AgentState) -> Dict[str, Any]:
        """Document detective node - analyzes PDF report."""
        
        logger.info("Starting document analysis", pdf_path=state.get('pdf_path'))
        
        if not state.get('pdf_path'):
            return {'detective_status': {'doc_analyst': 'skipped'}}
        
        try:
            pdf_path = Path(state['pdf_path'])
            if not pdf_path.exists():
                return {'evidence_errors': [f'PDF not found: {pdf_path}']}
            
            # Analyze PDF
            pdf_analysis = await self.pdf_tool.analyze_pdf(pdf_path)
            
            # Cross-reference with code evidence
            claimed_paths = pdf_analysis['claimed_paths']
            verified_paths = []
            hallucinated_paths = []
            
            if state.get('evidences') and state['evidences'].code:
                # This would need access to actual files - simplified here
                pass
            
            pdf_evidence = PdfForensicEvidence(
                cognitive_depth={
                    k: v.get('context', '')[:200] 
                    for k, v in pdf_analysis['theoretical_depth'].items() 
                    if v['found']
                },
                trust_debt_mentioned=pdf_analysis['theoretical_depth']['trust_debt']['found'],
                context_injection_paradox_mentioned=pdf_analysis['theoretical_depth']['context_injection_paradox']['found'],
                two_stage_state_machine_mentioned=pdf_analysis['theoretical_depth']['two_stage_state_machine']['found'],
                claimed_file_paths=claimed_paths,
                verified_paths=verified_paths,
                hallucinated_paths=hallucinated_paths,
                retrieval_snippets=pdf_analysis.get('retrieval', {})
            )
            
            # Store images for vision analysis
            images = pdf_analysis.get('images', [])
            
            return {
                'evidences': ForensicEvidenceCollection(
                    pdf=pdf_evidence,
                    raw_evidence={
                        'pdf_text': Evidence(
                            found=True,
                            content=pdf_analysis['text'],
                            location='pdf',
                            rationale="Extracted text used for concept matching and cross-reference against code evidence.",
                            confidence=0.9
                        ),
                        'pdf_retrieval': Evidence(
                            found=True,
                            content=str(pdf_analysis.get('retrieval', {})),
                            location='pdf_retrieval',
                            rationale="Concept snippets retrieved from chunked PDF text for targeted verification and cross-reference.",
                            confidence=0.8
                        ),
                        'pdf_images': Evidence(
                            found=bool(images),
                            content=images,
                            location='pdf_images',
                            rationale="Images extracted for multimodal diagram inspection.",
                            confidence=0.8 if images else 0.4
                        ),
                        'pdf_chunks': Evidence(
                            found=bool(pdf_analysis.get('chunks')),
                            content=str(pdf_analysis.get('chunks', []))[:2000],
                            location='pdf_chunks',
                            rationale="Chunked PDF text used for targeted retrieval queries.",
                            confidence=0.7 if pdf_analysis.get('chunks') else 0.4
                        ),
                    }
                ),
                'detective_status': {'doc_analyst': 'done'}
            }
            
        except Exception as e:
            logger.error("Document analysis failed", error=str(e))
            return {
                'evidence_errors': [f"Document analysis failed: {str(e)}"],
                'detective_status': {'doc_analyst': 'failed'}
            }
    
    async def vision_inspector(self, state: AgentState) -> Dict[str, Any]:
        """Vision detective node - analyzes diagrams."""
        
        logger.info("Starting vision inspection")
        
        if not state.get('evidences') or not state['evidences'].raw_evidence.get('pdf_images'):
            return {'detective_status': {'vision_inspector': 'skipped'}}
        
        try:
            images = state['evidences'].raw_evidence['pdf_images'].content
            if not isinstance(images, list):
                images = []
            
            # Analyze diagrams
            diagram_analyses = await self.vision_tool.analyze_diagrams(images)
            
            # Aggregate results
            diagram_types = [a['diagram_type'] for a in diagram_analyses]
            handshake_visualized = any(a['contains_reasoning_loop'] for a in diagram_analyses)
            data_labeled = any(a['data_payloads_labeled'] for a in diagram_analyses)
            
            image_evidence = ImageForensicEvidence(
                image_count=len(diagram_analyses),
                diagram_types=diagram_types,
                handshake_visualized=handshake_visualized,
                flow_description=str(diagram_analyses),
                contains_reasoning_loop=handshake_visualized,
                data_payloads_labeled=data_labeled
            )
            
            return {
                'evidences': ForensicEvidenceCollection(
                    images=image_evidence,
                    raw_evidence={
                        'diagram_analysis': Evidence(
                            found=True,
                            content=str(diagram_analyses),
                            location='vision',
                            rationale="Multimodal analysis of extracted diagrams for flow and labeling fidelity.",
                            confidence=0.8
                        )
                    }
                ),
                'detective_status': {'vision_inspector': 'done'}
            }
            
        except Exception as e:
            logger.error("Vision inspection failed", error=str(e))
            return {
                'evidence_errors': [f"Vision inspection failed: {str(e)}"],
                'detective_status': {'vision_inspector': 'failed'}
            }
