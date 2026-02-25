import tempfile
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
import os
import stat
import subprocess
from typing import Optional, List


class SandboxEnvironment:
    """Secure sandbox for running untrusted code operations."""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or tempfile.mkdtemp()
        self.current_dir: Optional[Path] = None
    
    @asynccontextmanager
    async def __call__(self):
        """Context manager for sandbox operations."""
        try:
            self.current_dir = Path(tempfile.mkdtemp(dir=self.base_dir))
            # Set restrictive permissions
            os.chmod(self.current_dir, 0o700)
            
            yield self
            
        finally:
            if self.current_dir and self.current_dir.exists():
                # Force remove read-only files
                def on_rm_error(func, path, exc_info):
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                
                shutil.rmtree(self.current_dir, onerror=on_rm_error)
    
    async def run_command(self, cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run command in sandbox with timeout."""
        if not self.current_dir:
            raise RuntimeError("Sandbox not initialized")
        
        return subprocess.run(
            cmd,
            cwd=self.current_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )