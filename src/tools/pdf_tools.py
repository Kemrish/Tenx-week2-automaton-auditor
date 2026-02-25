from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
from docling.document import Document
from docling.reader import DocumentReader
import re


class PDFForensicTool:
    """PDF analysis using Docling."""
    
    def __init__(self):
        self.reader = DocumentReader()
    
    async def analyze_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract and analyze PDF content."""
        
        # Read PDF
        doc = self.reader.read(pdf_path)
        
        # Extract text
        text = doc.text
        
        # Extract images (for vision analysis)
        images = []
        for page in doc.pages:
            for element in page.elements:
                if element.type == 'image':
                    images.append({
                        'page': page.number,
                        'bbox': element.bbox,
                        'data': element.data
                    })
        
        # Analyze theoretical depth
        theoretical_depth = await self._analyze_theoretical_depth(text)
        
        # Extract claimed file paths
        claimed_paths = self._extract_file_paths(text)
        
        return {
            'text': text[:2000],  # Truncate for context
            'images': images,
            'theoretical_depth': theoretical_depth,
            'claimed_paths': claimed_paths,
            'page_count': len(doc.pages)
        }
    
    async def _analyze_theoretical_depth(self, text: str) -> Dict[str, Any]:
        """Analyze depth of theoretical concepts."""
        
        concepts = {
            'cognitive_debt': {
                'patterns': [
                    r'cognitive\s+debt',
                    r'Margaret\s+Storey',
                    r'Storey\s+\(\d{4}\)'
                ],
                'found': False,
                'context': None
            },
            'trust_debt': {
                'patterns': [r'trust\s+debt', r'trust\s+building'],
                'found': False,
                'context': None
            },
            'context_injection_paradox': {
                'patterns': [
                    r'context[-\s]injection\s+paradox',
                    r'context\s+injection'
                ],
                'found': False,
                'context': None
            },
            'two_stage_state_machine': {
                'patterns': [
                    r'two[-\s]stage\s+state\s+machine',
                    r'state\s+machine',
                    r'finite\s+state'
                ],
                'found': False,
                'context': None
            }
        }
        
        for concept, data in concepts.items():
            for pattern in data['patterns']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['found'] = True
                    # Extract surrounding context (200 chars)
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    data['context'] = text[start:end]
                    break
        
        return concepts
    
    def _extract_file_paths(self, text: str) -> List[str]:
        """Extract file paths mentioned in text."""
        
        # Pattern for file paths
        path_pattern = r'`?([a-zA-Z0-9_/\\-]+\.[a-zA-Z0-9]+)`?'
        
        matches = re.findall(path_pattern, text)
        
        # Filter to reasonable paths
        valid_extensions = ['.py', '.ts', '.js', '.json', '.yaml', '.yml', '.md']
        paths = []
        
        for match in matches:
            if any(match.endswith(ext) for ext in valid_extensions):
                # Clean up path
                path = match.strip('`').strip()
                if path not in paths:
                    paths.append(path)
        
        return paths