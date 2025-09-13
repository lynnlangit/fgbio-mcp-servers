"""FastMCP server for fgbio BAM manipulation tools."""

import logging
from typing import Optional, Literal
from pathlib import Path

from fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

from .fgbio_wrapper import FgbioWrapper, FgbioError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP("fgbio-bam-mcp")

# Global fgbio wrapper instance
fgbio_wrapper = None


def get_fgbio_wrapper() -> FgbioWrapper:
    """Get or create the fgbio wrapper instance."""
    global fgbio_wrapper
    if fgbio_wrapper is None:
        try:
            fgbio_wrapper = FgbioWrapper()
        except FgbioError as e:
            logger.error(f"Failed to initialize fgbio wrapper: {e}")
            raise
    return fgbio_wrapper


class SortBamRequest(BaseModel):
    """Request model for SortBam tool."""
    
    input_bam: str = Field(
        ...,
        description="Path to the input BAM file to sort"
    )
    output_bam: str = Field(
        ...,
        description="Path where the sorted BAM file will be written"
    )
    sort_order: Literal["coordinate", "queryname", "random", "unsorted"] = Field(
        default="coordinate",
        description="Sort order for the BAM file"
    )
    temp_dir: Optional[str] = Field(
        default=None,
        description="Temporary directory for sorting operations"
    )
    max_records_in_ram: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum number of records to keep in memory during sorting"
    )
    
    @field_validator('input_bam', 'output_bam')
    @classmethod
    def validate_paths(cls, v):
        """Validate that paths are not empty strings."""
        if not v or not v.strip():
            raise ValueError("Path cannot be empty")
        return v.strip()
    
    @field_validator('temp_dir')
    @classmethod
    def validate_temp_dir(cls, v):
        """Validate temp directory if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Temp directory cannot be empty string")
        return v


class SortBamResponse(BaseModel):
    """Response model for SortBam tool."""
    
    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Description of the operation result")
    input_file: str = Field(description="Path to the input BAM file")
    output_file: str = Field(description="Path to the output BAM file")
    sort_order: str = Field(description="Sort order used")
    command_executed: Optional[str] = Field(
        default=None,
        description="The fgbio command that was executed"
    )
    stdout: Optional[str] = Field(
        default=None,
        description="Standard output from the fgbio command"
    )
    stderr: Optional[str] = Field(
        default=None,
        description="Standard error from the fgbio command"
    )


@mcp.tool()
def sort_bam(request: SortBamRequest) -> SortBamResponse:
    """
    Sort a BAM file using fgbio SortBam tool.
    
    This tool sorts BAM files according to the specified sort order.
    The most common sort orders are:
    - coordinate: Sort by genomic coordinates (default)
    - queryname: Sort by read name
    - random: Random order
    - unsorted: No specific order
    
    The tool validates input files exist and output directories are writable
    before executing the fgbio command.
    
    Args:
        request: SortBamRequest containing the sorting parameters
        
    Returns:
        SortBamResponse with the operation results
    """
    try:
        logger.info(f"Sorting BAM file: {request.input_bam} -> {request.output_bam}")
        
        # Get the fgbio wrapper
        wrapper = get_fgbio_wrapper()
        
        # Execute the sort operation
        result = wrapper.sort_bam(
            input_bam=request.input_bam,
            output_bam=request.output_bam,
            sort_order=request.sort_order,
            temp_dir=request.temp_dir,
            max_records_in_ram=request.max_records_in_ram
        )
        
        # Check if output file was created
        output_path = Path(request.output_bam)
        if not output_path.exists():
            raise FgbioError("Output BAM file was not created")
        
        return SortBamResponse(
            success=True,
            message=f"Successfully sorted BAM file with sort order '{request.sort_order}'",
            input_file=request.input_bam,
            output_file=request.output_bam,
            sort_order=request.sort_order,
            command_executed=result.get("command"),
            stdout=result.get("stdout"),
            stderr=result.get("stderr")
        )
        
    except FgbioError as e:
        logger.error(f"fgbio error in sort_bam: {e}")
        return SortBamResponse(
            success=False,
            message=f"fgbio error: {str(e)}",
            input_file=request.input_bam,
            output_file=request.output_bam,
            sort_order=request.sort_order
        )
    except Exception as e:
        logger.error(f"Unexpected error in sort_bam: {e}")
        return SortBamResponse(
            success=False,
            message=f"Unexpected error: {str(e)}",
            input_file=request.input_bam,
            output_file=request.output_bam,
            sort_order=request.sort_order
        )


def main():
    """Main entry point for the MCP server."""
    try:
        logger.info("Starting fgbio BAM MCP server...")
        
        # Test fgbio availability on startup
        get_fgbio_wrapper()
        
        logger.info("fgbio BAM MCP server initialized successfully")
        mcp.run()
        
    except FgbioError as e:
        logger.error(f"Failed to start server due to fgbio error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


if __name__ == "__main__":
    main()