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

            chunks = self._chunk_text(text)
            retrieval = self._retrieve_key_concepts(chunks)
            
            return {
                'text': text[:2000],  # Truncate for context
                'images': images,
                'theoretical_depth': theoretical_depth,
                'claimed_paths': claimed_paths,
                'page_count': len(doc.pages) if hasattr(doc, 'pages') else 0,
                'retrieval': retrieval,
                'chunks': chunks,
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
            try:
                import fitz  # PyMuPDF
            except Exception:
                fitz = None
            
            text = ""
            images = []
            
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text()

            # Extract images via PyMuPDF if available
            images = []
            if fitz:
                doc = fitz.open(str(pdf_path))
                for page_index in range(len(doc)):
                    page = doc[page_index]
                    for img_index, img in enumerate(page.get_images(full=True)):
                        xref = img[0]
                        base = doc.extract_image(xref)
                        image_bytes = base.get("image")
                        if image_bytes:
                            images.append({
                                "page": page_index + 1,
                                "data": image_bytes,
                            })
            
            theoretical_depth = await self._analyze_theoretical_depth(text)
            claimed_paths = self._extract_file_paths(text)
            chunks = self._chunk_text(text)
            retrieval = self._retrieve_key_concepts(chunks)
            
            return {
                'text': text[:2000],
                'images': images,
                'theoretical_depth': theoretical_depth,
                'claimed_paths': claimed_paths,
                'page_count': len(reader.pages),
                'retrieval': retrieval,
                'chunks': chunks,
            }
            
        except ImportError:
            # If PyPDF2 also not available, return empty
            return {
                'text': "PDF text extraction failed",
                'images': [],
                'theoretical_depth': {},
                'claimed_paths': [],
                'page_count': 0,
                'retrieval': {},
                'chunks': []
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

    def _retrieve_key_concepts(self, chunks: List[Dict[str, str]]) -> Dict[str, List[str]]:
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
                for chunk in chunks:
                    for match in re.finditer(pattern, chunk["text"], re.IGNORECASE):
                        start = max(0, match.start() - 120)
                        end = min(len(chunk["text"]), match.end() + 120)
                        snippet = chunk["text"][start:end].replace("\n", " ")
                        matches.append(
                            f"{chunk['id']}: {shorten(snippet, width=220, placeholder='...')}"
                        )
            if matches:
                snippets[key] = matches[:3]

        return snippets

    def _chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 120) -> List[Dict[str, str]]:
        """Chunk text into overlapping segments for targeted retrieval."""
        if not text:
            return []
        chunks: List[Dict[str, str]] = []
        start = 0
        idx = 1
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"id": f"chunk_{idx}", "text": chunk_text})
                idx += 1
            if end == len(text):
                break
            start = max(0, end - overlap)
        return chunks
