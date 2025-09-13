"""fgbio BAM MCP Server package."""

from .fgbio_wrapper import FgbioWrapper, FgbioError
from .server import main

__version__ = "0.1.0"
__all__ = ["FgbioWrapper", "FgbioError", "main"]