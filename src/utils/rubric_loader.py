import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class RubricLoader:
    """Load and manage the grading rubric."""
    
    _rubric_cache: Optional[Dict[str, Any]] = None
    _rubric_path: Optional[Path] = None
    
    @classmethod
    def load_rubric(cls, rubric_path: Optional[str] = None) -> Dict[str, Any]:
        """Load the rubric from JSON file."""
        
        # Return cached version if available
        if cls._rubric_cache is not None:
            return cls._rubric_cache
        
        # Determine rubric path
        if rubric_path:
            path = Path(rubric_path)
        else:
            # Default path relative to project root
            # Try multiple possible locations
            possible_paths = [
                Path("rubric/week2_rubric.json"),
                Path("../rubric/week2_rubric.json"),
                Path(__file__).parent.parent.parent / "rubric" / "week2_rubric.json",
                Path.cwd() / "rubric" / "week2_rubric.json",
            ]
            
            for p in possible_paths:
                if p.exists():
                    path = p
                    break
            else:
                # If no rubric found, create a default one
                logger.warning("Rubric file not found, using default rubric")
                return cls._create_default_rubric()
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                rubric = json.load(f)
            
            cls._rubric_cache = rubric
            cls._rubric_path = path
            logger.info(f"Loaded rubric from {path}")
            return rubric
            
        except Exception as e:
            logger.error(f"Failed to load rubric: {e}")
            # Return default rubric as fallback
            return cls._create_default_rubric()
    
    @classmethod
    def _create_default_rubric(cls) -> Dict[str, Any]:
        """Create a default rubric if file not found."""
        
        default_rubric = {
            "rubric_metadata": {
                "rubric_name": "Default Week 2 Rubric",
                "grading_target": "Week 2 Auditor Repository",
                "version": "1.0.0"
            },
            "dimensions": [
                {
                    "id": "forensic_accuracy_code",
                    "name": "Forensic Accuracy (Codebase)",
                    "target_artifact": "github_repo",
                    "forensic_instruction": "Verify code structure and tool registration",
                    "judicial_logic": {
                        "prosecutor": "Check for missing error handling",
                        "defense": "Look for creative solutions",
                        "tech_lead": "Assess maintainability"
                    }
                },
                {
                    "id": "forensic_accuracy_docs",
                    "name": "Forensic Accuracy (Documentation)",
                    "target_artifact": "pdf_report",
                    "forensic_instruction": "Verify theoretical depth and cross-reference claims",
                    "judicial_logic": {
                        "prosecutor": "Check for hallucinated claims",
                        "defense": "Identify theoretical alignment",
                        "tech_lead": "Verify implementation matches docs"
                    }
                },
                {
                    "id": "judicial_nuance",
                    "name": "Judicial Nuance & Dialectics",
                    "target_artifact": "github_repo",
                    "forensic_instruction": "Verify distinct judge personas and parallel execution",
                    "judicial_logic": {
                        "prosecutor": "Check for persona collusion",
                        "defense": "Look for contrarian instructions",
                        "tech_lead": "Evaluate synthesis algorithm"
                    }
                },
                {
                    "id": "langgraph_architecture",
                    "name": "LangGraph Orchestration Rigor",
                    "target_artifact": "github_repo",
                    "forensic_instruction": "Analyze StateGraph for parallel branches and error handling",
                    "judicial_logic": {
                        "prosecutor": "Check for linear fraud",
                        "defense": "Support robust state transitions",
                        "tech_lead": "Evaluate checkpointing"
                    }
                }
            ],
            "synthesis_rules": {
                "security_override": "Security flaws cap total score at 3",
                "fact_supremacy": "Facts overrule opinions",
                "dissent_requirement": "Summarize judge disagreements"
            }
        }
        
        cls._rubric_cache = default_rubric
        return default_rubric
    
    @classmethod
    def get_criterion(cls, criterion_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific criterion by ID."""
        rubric = cls.load_rubric()
        for dimension in rubric.get("dimensions", []):
            if dimension.get("id") == criterion_id:
                return dimension
        return None
    
    @classmethod
    def get_judicial_logic(cls, criterion_id: str, judge: str) -> Optional[str]:
        """Get judicial logic for a specific criterion and judge."""
        criterion = cls.get_criterion(criterion_id)
        if criterion and "judicial_logic" in criterion:
            return criterion["judicial_logic"].get(judge.lower())
        return None
    
    @classmethod
    def reload_rubric(cls) -> Dict[str, Any]:
        """Force reload the rubric from file."""
        cls._rubric_cache = None
        return cls.load_rubric()