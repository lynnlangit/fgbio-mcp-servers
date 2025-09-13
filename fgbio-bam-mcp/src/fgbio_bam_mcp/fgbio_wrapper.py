"""Wrapper class for executing fgbio commands."""

import subprocess
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class FgbioError(Exception):
    """Exception raised when fgbio command fails."""
    pass


class FgbioWrapper:
    """Wrapper class for executing fgbio commands."""
    
    def __init__(self, fgbio_command: str = "fgbio"):
        """Initialize the fgbio wrapper.
        
        Args:
            fgbio_command: Path or command to the fgbio executable
        """
        self.fgbio_command = fgbio_command
        self._validate_fgbio_available()
    
    def _validate_fgbio_available(self) -> None:
        """Check if fgbio is available in the system."""
        try:
            result = subprocess.run(
                [self.fgbio_command, "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            # fgbio --version returns exit code 1 but this is normal behavior
            # We just need to check that we can execute it and get version output
            version_output = result.stderr.strip() or result.stdout.strip()
            if not version_output or "Version:" not in version_output:
                raise FgbioError(f"fgbio command returned unexpected output: {version_output}")
            logger.info(f"fgbio version: {version_output}")
        except subprocess.TimeoutExpired:
            raise FgbioError("fgbio command timed out")
        except FileNotFoundError:
            raise FgbioError(f"fgbio command not found: {self.fgbio_command}")
    
    def _validate_file_path(self, file_path: str, must_exist: bool = True) -> Path:
        """Validate and convert file path to Path object.
        
        Args:
            file_path: Path to validate
            must_exist: Whether the file must already exist
            
        Returns:
            Validated Path object
            
        Raises:
            FgbioError: If validation fails
        """
        path = Path(file_path)
        
        if must_exist and not path.exists():
            raise FgbioError(f"File does not exist: {file_path}")
        
        if must_exist and not path.is_file():
            raise FgbioError(f"Path is not a file: {file_path}")
        
        # For output files, check if parent directory exists
        if not must_exist:
            parent = path.parent
            if not parent.exists():
                raise FgbioError(f"Output directory does not exist: {parent}")
        
        return path
    
    def _build_command(self, tool_name: str, params: Dict[str, Any]) -> List[str]:
        """Build the fgbio command with parameters.
        
        Args:
            tool_name: Name of the fgbio tool to run
            params: Dictionary of parameters
            
        Returns:
            List of command components
        """
        cmd = [self.fgbio_command, tool_name]
        
        for key, value in params.items():
            if value is None:
                continue
            
            # Convert parameter name to kebab-case for fgbio
            param_name = key.replace('_', '-')
            
            if isinstance(value, bool):
                if value:
                    cmd.append(f"--{param_name}")
            elif isinstance(value, list):
                for item in value:
                    cmd.extend([f"--{param_name}", str(item)])
            else:
                cmd.extend([f"--{param_name}", str(value)])
        
        return cmd
    
    def run_command(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a fgbio command with the given parameters.
        
        Args:
            tool_name: Name of the fgbio tool to run
            params: Dictionary of parameters for the tool
            
        Returns:
            Dictionary containing execution results
            
        Raises:
            FgbioError: If command execution fails
        """
        try:
            cmd = self._build_command(tool_name, params)
            logger.info(f"Executing command: {' '.join(shlex.quote(str(c)) for c in cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout for long-running operations
            )
            
            if result.returncode != 0:
                raise FgbioError(
                    f"fgbio {tool_name} failed with return code {result.returncode}: "
                    f"{result.stderr}"
                )
            
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "command": ' '.join(shlex.quote(str(c)) for c in cmd)
            }
            
        except subprocess.TimeoutExpired:
            raise FgbioError(f"fgbio {tool_name} command timed out after 1 hour")
        except Exception as e:
            raise FgbioError(f"Failed to execute fgbio {tool_name}: {str(e)}")
    
    def sort_bam(self, input_bam: str, output_bam: str, sort_order: str = "coordinate", 
                 temp_dir: Optional[str] = None, max_records_in_ram: Optional[int] = None) -> Dict[str, Any]:
        """Sort a BAM file using fgbio SortBam.
        
        Args:
            input_bam: Path to input BAM file
            output_bam: Path to output BAM file
            sort_order: Sort order (coordinate, queryname, random, unsorted)
            temp_dir: Temporary directory for sorting
            max_records_in_ram: Maximum records to keep in memory
            
        Returns:
            Dictionary containing execution results
        """
        # Validate input file exists
        self._validate_file_path(input_bam, must_exist=True)
        
        # Validate output path is writable
        self._validate_file_path(output_bam, must_exist=False)
        
        params = {
            "input": input_bam,
            "output": output_bam,
            "sort_order": sort_order
        }
        
        if temp_dir:
            params["tmp_dir"] = temp_dir
        
        if max_records_in_ram:
            params["max_records_in_ram"] = max_records_in_ram
        
        return self.run_command("SortBam", params)