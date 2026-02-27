import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Tuple
import tree_sitter
from tree_sitter_languages import get_language, get_parser


class ASTForensicTool:
    """Advanced AST parsing for code forensic analysis."""
    
    def __init__(self):
        self.supported_languages = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
        }
        
        # Initialize parsers for each language
        self.parsers = {}
        for ext, lang in self.supported_languages.items():
            if lang != 'markdown' and lang != 'json' and lang != 'yaml':
                try:
                    self.parsers[lang] = get_parser(lang)
                except:
                    pass
    
    async def analyze_codebase(self, repo_path: Path) -> Dict[str, Any]:
        """Perform comprehensive codebase analysis."""
        
        result = {
            'architecture_notes': await self._find_architecture_notes(repo_path),
            'tool_registration': await self._analyze_tool_registration(repo_path),
            'system_prompt': await self._analyze_system_prompt(repo_path),
            'middleware': await self._analyze_middleware(repo_path),
            'hashing': await self._analyze_hashing(repo_path),
            'trace_writing': await self._analyze_trace_writing(repo_path),
            'state_models': await self._analyze_state_models(repo_path),
            'graph_structure': await self._analyze_langgraph_structure(repo_path),
        }
        
        return result
    
    async def _find_architecture_notes(self, repo_path: Path) -> Dict[str, Any]:
        """Find and analyze ARCHITECTURE_NOTES.md."""
        notes_path = repo_path / 'ARCHITECTURE_NOTES.md'
        
        if not notes_path.exists():
            return {'exists': False, 'paths': []}
        
        content = notes_path.read_text()
        
        # Extract file paths mentioned
        path_pattern = r'`?([a-zA-Z0-9_/\\-]+\.(ts|js|py|json))`?'
        paths = re.findall(path_pattern, content)
        
        return {
            'exists': True,
            'content': content[:500],  # Truncate for context
            'paths': [p[0] for p in paths]
        }
    
    async def _analyze_tool_registration(self, repo_path: Path) -> Dict[str, Any]:
        """Verify tool registration in codebase."""
        
        # Look for tool definitions
        tool_patterns = [
            r'@tool',
            r'StructuredTool',
            r'Tool\(',
            r'register_tool',
            r'add_tool',
            r'add_tools',
            r'tools\s*=\s*\[',
            r'select_active_intent',
            r'def select_active_intent',
            r'function select_active_intent',
            r'const select_active_intent',
            r'tool\(\s*[\'"`]select_active_intent[\'"`]',
        ]
        
        return await self._search_files(repo_path, tool_patterns, ['src/tools/', 'src/'])
    
    async def _analyze_system_prompt(self, repo_path: Path) -> Dict[str, Any]:
        """Check system prompt for required instructions."""
        
        instruction_patterns = [
            r'You must call select_active_intent',
            r'call the select_active_intent tool',
            r'use select_active_intent',
            r'select_active_intent\(\s*\)',
            r'role\s*=\s*[\'"`]system[\'"`]',
            r'\("system"\s*,',
            r'System\s*Prompt',
            r'You must',
            r'Tool',
        ]
        
        return await self._search_files(
            repo_path, 
            instruction_patterns, 
            ['src/core/prompts/', 'src/prompts/', 'src/']
        )
    
    async def _analyze_middleware(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze hook/middleware implementation."""
        
        hook_patterns = [
            r'def validate_intent',
            r'function validateIntent',
            r'active_intents\.yaml',
            r'scope_violation',
            r'if.*scope.*violation',
        ]
        
        return await self._search_files(
            repo_path,
            hook_patterns,
            ['src/hooks/', 'src/middleware/']
        )
    
    async def _analyze_hashing(self, repo_path: Path) -> Dict[str, Any]:
        """Check for hash implementation."""
        
        hash_patterns = [
            r'hash',
            r'sha256',
            r'crypto\.createHash',
            r'hashlib',
            r'create_hash',
        ]
        
        return await self._search_files(repo_path, hash_patterns, ['src/'])
    
    async def _analyze_trace_writing(self, repo_path: Path) -> Dict[str, Any]:
        """Check for trace writing to JSONL."""
        
        trace_patterns = [
            r'agent_trace\.jsonl',
            r'write.*trace',
            r'append.*jsonl',
            r'log.*interaction',
        ]
        
        return await self._search_files(repo_path, trace_patterns, ['src/'])
    
    async def _analyze_state_models(self, repo_path: Path) -> Dict[str, Any]:
        """Check for Pydantic state models."""
        
        pydantic_patterns = [
            r'BaseModel',
            r'Field\(',
            r'@validator',
            r'pydantic',
        ]
        
        return await self._search_files(
            repo_path,
            pydantic_patterns,
            ['src/state.py', 'src/graph.py']
        )

    async def _analyze_langgraph_structure(self, repo_path: Path) -> Dict[str, Any]:
        """Infer graph structure: fan-out, fan-in, conditional edges, checkpointers."""
        edges: List[Tuple[str, str]] = []
        nodes: Set[str] = set()
        conditional_edges = False
        files_scanned: Set[str] = set()

        for file_path in repo_path.rglob("*.py"):
            if not file_path.is_file():
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            files_scanned.add(str(file_path.relative_to(repo_path)))
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                else:
                    continue

                if func_name == "add_node" and node.args:
                    first = node.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        nodes.add(first.value)

                if func_name == "add_edge" and len(node.args) >= 2:
                    src = node.args[0]
                    dst = node.args[1]
                    if (
                        isinstance(src, ast.Constant)
                        and isinstance(dst, ast.Constant)
                        and isinstance(src.value, str)
                        and isinstance(dst.value, str)
                    ):
                        edges.append((src.value, dst.value))

                if func_name == "add_conditional_edges":
                    conditional_edges = True
                    if node.args:
                        src = node.args[0]
                        if isinstance(src, ast.Constant) and isinstance(src.value, str):
                            nodes.add(src.value)

        in_degree: Dict[str, int] = defaultdict(int)
        out_degree: Dict[str, int] = defaultdict(int)
        for src, dst in edges:
            out_degree[src] += 1
            in_degree[dst] += 1

        fan_out = any(count > 1 for count in out_degree.values())
        fan_in = any(count > 1 for count in in_degree.values())

        # Check for checkpointer usage
        checkpointer_patterns = [
            r'checkpointer\s*=',
            r'compile\(\s*checkpointer=',
            r'MemorySaver\(',
            r'SqliteSaver\(',
            r'PostgresSaver\(',
            r'InMemorySaver\(',
        ]
        checkpointer = await self._search_files(repo_path, checkpointer_patterns, ['src/'])

        return {
            'fan_out': fan_out,
            'fan_in': fan_in,
            'conditional_edges': conditional_edges,
            'checkpointer_used': checkpointer['found'],
            'edge_count': len(edges),
            'node_count': len(nodes),
            'files_scanned': list(files_scanned),
        }
    
    async def _search_files(self, repo_path: Path, patterns: List[str], 
                           search_paths: List[str]) -> Dict[str, Any]:
        """Search for patterns in files within search paths."""
        
        matches = []
        locations = []
        
        for search_path in search_paths:
            full_path = repo_path / search_path
            if not full_path.exists():
                continue
            
            if full_path.is_file():
                files = [full_path]
            else:
                files = full_path.rglob('*')
            
            for file_path in files:
                if not file_path.is_file():
                    continue
                
                try:
                    content = file_path.read_text(encoding="utf-8")
                    for pattern in patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            matches.append(pattern)
                            locations.append(str(file_path.relative_to(repo_path)))
                            break
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        return {
            'found': len(matches) > 0,
            'patterns_found': list(set(matches)),
            'locations': list(set(locations))
        }
    
    async def parse_ast(self, file_path: Path) -> Optional[ast.AST]:
        """Parse Python file to AST."""
        if file_path.suffix != '.py':
            return None
        
        try:
            content = file_path.read_text()
            return ast.parse(content)
        except SyntaxError:
            return None
    
    async def verify_function_export(self, file_path: Path, function_name: str) -> bool:
        """Verify if function is properly exported."""
        
        # Python
        if file_path.suffix == '.py':
            tree = await self.parse_ast(file_path)
            if not tree:
                return False
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    return True
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == function_name:
                            return True
        
        # TypeScript/JavaScript
        elif file_path.suffix in ['.ts', '.js', '.tsx', '.jsx']:
            content = file_path.read_text()
            export_patterns = [
                rf'export\s+(const|let|var|function)\s+{function_name}',
                rf'export\s+{{\s*{function_name}\s*}}',
                rf'module\.exports\s*=\s*{{\s*{function_name}',
            ]
            
            for pattern in export_patterns:
                if re.search(pattern, content):
                    return True
        
        return False
