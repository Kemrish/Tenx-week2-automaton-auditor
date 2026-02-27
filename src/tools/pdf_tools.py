from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
import re
import io
from collections import defaultdict
from textwrap import shorten

try:
    from docling.document_converter import DocumentConverter  # New import path
except ImportError:  # Allow running without docling when PDFs are not used
    DocumentConverter = None


class PDFForensicTool:
    """PDF analysis using Docling (updated for v2+)."""
    
    def __init__(self):
        # Initialize the document converter (new in docling v2)
        self.converter = DocumentConverter() if DocumentConverter else None
    
    async def analyze_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract and analyze PDF content."""
        
        try:
            if self.converter is None:
                return await self._fallback_analysis(pdf_path)

            # Convert PDF to document (new API in v2)
            result = self.converter.convert(pdf_path)
            
            # Get the document
            doc = result.document
            
            # Extract text - different access pattern in v2
            text = doc.text if hasattr(doc, 'text') else str(doc)

            # Extract images if available
            images = []
            if hasattr(doc, 'pages'):
                for page_num, page in enumerate(doc.pages):
                    if hasattr(page, 'elements'):
                        for element in page.elements:
                            if hasattr(element, 'type') and element.type == 'image':
                                images.append({
                                    'page': page_num + 1,
                                    'data': element.get_image() if hasattr(element, 'get_image') else None
                                })
            
            # Analyze theoretical depth
            theoretical_depth = await self._analyze_theoretical_depth(text)
            
            # Extract claimed file paths
            claimed_paths = self._extract_file_paths(text)

            retrieval = self._retrieve_key_concepts(text)
            
            return {
                'text': text[:2000],  # Truncate for context
                'images': images,
                'theoretical_depth': theoretical_depth,
                'claimed_paths': claimed_paths,
                'page_count': len(doc.pages) if hasattr(doc, 'pages') else 0,
                'retrieval': retrieval
            }
            
        except Exception as e:
            # Fallback to simple text extraction if docling fails
            print(f"Docling conversion failed: {e}, trying fallback...")
            return await self._fallback_analysis(pdf_path)
    
    async def _fallback_analysis(self, pdf_path: Path) -> Dict[str, Any]:
        """Fallback method if docling fails."""
        try:
            # Try to extract text using PyPDF2 or similar
            # For now, return minimal info
            import PyPDF2
            
            text = ""
            images = []
            
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text()
            
            theoretical_depth = await self._analyze_theoretical_depth(text)
            claimed_paths = self._extract_file_paths(text)
            retrieval = self._retrieve_key_concepts(text)
            
            return {
                'text': text[:2000],
                'images': images,
                'theoretical_depth': theoretical_depth,
                'claimed_paths': claimed_paths,
                'page_count': len(reader.pages),
                'retrieval': retrieval
            }
            
        except ImportError:
            # If PyPDF2 also not available, return empty
            return {
                'text': "PDF text extraction failed",
                'images': [],
                'theoretical_depth': {},
                'claimed_paths': [],
                'page_count': 0,
                'retrieval': {}
            }
    
    async def _analyze_theoretical_depth(self, text: str) -> Dict[str, Any]:
        """Analyze depth of theoretical concepts."""
        
        concepts = {
            'cognitive_debt': {
                'patterns': [
                    r'cognitive\s+debt',
                    r'Margaret\s+Storey',
                    r'Storey\s*\(\d{4}\)'
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

    def _retrieve_key_concepts(self, text: str) -> Dict[str, List[str]]:
        """Lightweight retrieval of key concepts with contextual snippets."""
        queries = {
            "cognitive_debt": [r'cognitive\s+debt', r'Margaret\s+Storey'],
            "trust_debt": [r'trust\s+debt', r'trust\s+building'],
            "context_injection_paradox": [r'context[-\s]injection\s+paradox', r'context\s+injection'],
            "two_stage_state_machine": [r'two[-\s]stage\s+state\s+machine', r'finite\s+state'],
            "langgraph": [r'langgraph', r'state\s+graph'],
        }

        snippets: Dict[str, List[str]] = {}
        for key, patterns in queries.items():
            matches = []
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    start = max(0, match.start() - 120)
                    end = min(len(text), match.end() + 120)
                    snippet = text[start:end].replace("\n", " ")
                    matches.append(shorten(snippet, width=240, placeholder="..."))
            if matches:
                snippets[key] = matches[:3]

        return snippets
