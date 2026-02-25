from pathlib import Path
from typing import List, Dict, Any, Optional
import base64
from PIL import Image
import io
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


class VisionForensicTool:
    """Multimodal analysis of diagrams."""
    
    def __init__(self, model_name: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, max_tokens=1000)
    
    async def analyze_diagrams(self, images: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze multiple diagrams from PDF."""
        
        results = []
        
        for idx, img_data in enumerate(images):
            result = await self._analyze_single_diagram(img_data, idx)
            results.append(result)
        
        return results
    
    async def _analyze_single_diagram(self, img_data: Dict, index: int) -> Dict[str, Any]:
        """Analyze a single diagram using vision LLM."""
        
        # Convert image data to base64
        img = img_data['data']
        if isinstance(img, bytes):
            img_base64 = base64.b64encode(img).decode('utf-8')
        else:
            # Assume it's already bytes-like
            img_base64 = base64.b64encode(img).decode('utf-8')
        
        # Create message with image
        message = HumanMessage(
            content=[
                {
                    "type": "text", 
                    "text": """Analyze this diagram for the Automaton Auditor system. Answer:
                    1. What type of diagram is this? (Sequence, State Machine, Block, Flowchart)
                    2. Does it show the reasoning loop? (Agent -> Hook -> Context -> Agent)
                    3. Are data payloads labeled on connectors?
                    4. Describe the main flow visualized.
                    5. Rate diagram quality (1-5) and explain."""
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                }
            ]
        )
        
        response = await self.llm.ainvoke([message])
        
        # Parse response
        content = response.content
        
        # Extract structured data (simplified - in production use structured output)
        diagram_type = self._extract_diagram_type(content)
        contains_loop = 'agent -> hook' in content.lower() or 'reasoning loop' in content.lower()
        data_labeled = 'labeled' in content.lower() and 'data' in content.lower()
        
        return {
            'diagram_index': index,
            'page': img_data.get('page', 0),
            'diagram_type': diagram_type,
            'contains_reasoning_loop': contains_loop,
            'data_payloads_labeled': data_labeled,
            'flow_description': content[:500],
            'quality_score': self._extract_quality_score(content)
        }
    
    def _extract_diagram_type(self, content: str) -> str:
        """Extract diagram type from analysis."""
        types = ['Sequence', 'State Machine', 'Block', 'Flowchart']
        for t in types:
            if t.lower() in content.lower():
                return t
        return 'Unknown'
    
    def _extract_quality_score(self, content: str) -> int:
        """Extract quality score from analysis."""
        import re
        match = re.search(r'(\d+)/5', content)
        if match:
            return int(match.group(1))
        return 3  # Default