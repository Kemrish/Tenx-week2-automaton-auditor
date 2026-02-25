import os
import tempfile
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime
import git
from git.exc import GitCommandError
import shutil
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

from ..state import GitCommit, GitForensicEvidence


class GitForensicTool:
    """Advanced git forensic analysis tool."""
    
    def __init__(self, sandbox_dir: Optional[str] = None):
        self.sandbox_dir = sandbox_dir or tempfile.mkdtemp()
        self.repo_path: Optional[Path] = None
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def clone_repository(self, repo_url: str, branch: str = "main") -> Path:
        """Clone repository into sandbox with retry logic."""
        try:
            # Generate safe directory name
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            self.repo_path = Path(self.sandbox_dir) / f"{repo_name}_{datetime.now().timestamp()}"
            
            # Clone with progress monitoring
            repo = git.Repo.clone_from(
                repo_url, 
                self.repo_path,
                branch=branch,
                depth=50  # Limit history depth for performance
            )
            
            return self.repo_path
            
        except GitCommandError as e:
            raise RuntimeError(f"Git clone failed: {e}")
    
    async def analyze_git_history(self, max_commits: int = 50) -> GitForensicEvidence:
        """Extract and analyze git commit history."""
        if not self.repo_path:
            raise RuntimeError("Repository not cloned")
        
        repo = git.Repo(self.repo_path)
        
        commits = []
        for commit in repo.iter_commits(max_count=max_commits):
            git_commit = GitCommit(
                hash=commit.hexsha,
                message=commit.message.strip(),
                author=str(commit.author),
                timestamp=datetime.fromtimestamp(commit.committed_date),
                files_changed=list(commit.stats.files.keys())
            )
            commits.append(git_commit)
        
        # Analyze progression pattern
        messages = [c.message.lower() for c in commits]
        
        if len(commits) <= 1:
            pattern = 'monolithic'
        elif any('init' in m for m in messages[:2]) and any('feat' in m for m in messages):
            pattern = 'analysis_scaffolding_logic'
        elif len(commits) > 3 and len(set(messages)) > 2:
            pattern = 'analysis_scaffolding_logic'
        else:
            pattern = 'bulk_dump'
        
        return GitForensicEvidence(
            commits=commits,
            commit_count=len(commits),
            has_atomic_history=all(c.is_atomic for c in commits),
            progression_pattern=pattern,
            timestamps=[c.timestamp for c in commits]
        )
    
    async def get_file_at_commit(self, file_path: str, commit_hash: str) -> Optional[str]:
        """Retrieve file content at specific commit."""
        try:
            repo = git.Repo(self.repo_path)
            content = repo.git.show(f"{commit_hash}:{file_path}")
            return content
        except git.exc.GitCommandError:
            return None
    
    def cleanup(self):
        """Remove sandbox directory."""
        if self.repo_path and self.repo_path.exists():
            shutil.rmtree(self.repo_path, ignore_errors=True)
