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


class FilterBamRequest(BaseModel):
    """Request model for FilterBam tool."""
    
    input_bam: str = Field(
        ...,
        description="Path to the input BAM file to filter"
    )
    output_bam: str = Field(
        ...,
        description="Path where the filtered BAM file will be written"
    )
    rejects: Optional[str] = Field(
        default=None,
        description="Optional output file for rejected reads"
    )
    intervals: Optional[str] = Field(
        default=None,
        description="Optional intervals file to filter by"
    )
    remove_duplicates: bool = Field(
        default=True,
        description="Remove reads marked as duplicates"
    )
    remove_unmapped_reads: bool = Field(
        default=True,
        description="Remove unmapped reads"
    )
    min_map_q: int = Field(
        default=1,
        ge=0,
        description="Minimum mapping quality"
    )
    remove_single_end_mappings: bool = Field(
        default=False,
        description="Remove non-PE reads and reads with unmapped mates"
    )
    remove_secondary_alignments: bool = Field(
        default=True,
        description="Remove secondary alignments"
    )
    min_insert_size: Optional[int] = Field(
        default=None,
        gt=0,
        description="Minimum insert size"
    )
    max_insert_size: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum insert size"
    )
    min_mapped_bases: Optional[int] = Field(
        default=None,
        gt=0,
        description="Minimum number of mapped bases"
    )
    
    @field_validator('input_bam', 'output_bam')
    @classmethod
    def validate_paths(cls, v):
        """Validate that paths are not empty strings."""
        if not v or not v.strip():
            raise ValueError("Path cannot be empty")
        return v.strip()
    
    @field_validator('rejects', 'intervals')
    @classmethod
    def validate_optional_paths(cls, v):
        """Validate optional paths if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Path cannot be empty string")
        return v
    
    @field_validator('max_insert_size')
    @classmethod
    def validate_insert_sizes(cls, v, info):
        """Validate that max_insert_size > min_insert_size if both are provided."""
        if v is not None and 'min_insert_size' in info.data:
            min_size = info.data.get('min_insert_size')
            if min_size is not None and v <= min_size:
                raise ValueError("max_insert_size must be greater than min_insert_size")
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


class FilterBamResponse(BaseModel):
    """Response model for FilterBam tool."""
    
    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Description of the operation result")
    input_file: str = Field(description="Path to the input BAM file")
    output_file: str = Field(description="Path to the output BAM file")
    rejects_file: Optional[str] = Field(
        default=None,
        description="Path to the rejects BAM file if specified"
    )
    intervals_file: Optional[str] = Field(
        default=None,
        description="Path to the intervals file if specified"
    )
    filters_applied: dict = Field(description="Summary of filters that were applied")
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


@mcp.tool()
def filter_bam(request: FilterBamRequest) -> FilterBamResponse:
    """
    Filter a BAM file using fgbio FilterBam tool.
    
    This tool removes reads that may not be useful in downstream processing or 
    visualization. By default it removes unmapped reads, reads with MAPQ=0, 
    reads marked as secondary alignments, and reads marked as duplicates.
    
    Additional filters can be applied:
    - Minimum mapping quality threshold
    - Insert size filtering
    - Minimum mapped bases requirement
    - Interval-based filtering
    - Single-end mapping removal
    
    The tool validates input files exist and output directories are writable
    before executing the fgbio command.
    
    Args:
        request: FilterBamRequest containing the filtering parameters
        
    Returns:
        FilterBamResponse with the operation results
    """
    try:
        logger.info(f"Filtering BAM file: {request.input_bam} -> {request.output_bam}")
        
        # Get the fgbio wrapper
        wrapper = get_fgbio_wrapper()
        
        # Execute the filter operation
        result = wrapper.filter_bam(
            input_bam=request.input_bam,
            output_bam=request.output_bam,
            rejects=request.rejects,
            intervals=request.intervals,
            remove_duplicates=request.remove_duplicates,
            remove_unmapped_reads=request.remove_unmapped_reads,
            min_map_q=request.min_map_q,
            remove_single_end_mappings=request.remove_single_end_mappings,
            remove_secondary_alignments=request.remove_secondary_alignments,
            min_insert_size=request.min_insert_size,
            max_insert_size=request.max_insert_size,
            min_mapped_bases=request.min_mapped_bases
        )
        
        # Check if output file was created
        output_path = Path(request.output_bam)
        if not output_path.exists():
            raise FgbioError("Output BAM file was not created")
        
        # Create summary of filters applied
        filters_applied = {
            "remove_duplicates": request.remove_duplicates,
            "remove_unmapped_reads": request.remove_unmapped_reads,
            "min_map_q": request.min_map_q,
            "remove_single_end_mappings": request.remove_single_end_mappings,
            "remove_secondary_alignments": request.remove_secondary_alignments,
        }
        
        if request.min_insert_size is not None:
            filters_applied["min_insert_size"] = request.min_insert_size
        if request.max_insert_size is not None:
            filters_applied["max_insert_size"] = request.max_insert_size
        if request.min_mapped_bases is not None:
            filters_applied["min_mapped_bases"] = request.min_mapped_bases
        if request.intervals:
            filters_applied["intervals_filter"] = True
        
        return FilterBamResponse(
            success=True,
            message="Successfully filtered BAM file",
            input_file=request.input_bam,
            output_file=request.output_bam,
            rejects_file=request.rejects,
            intervals_file=request.intervals,
            filters_applied=filters_applied,
            command_executed=result.get("command"),
            stdout=result.get("stdout"),
            stderr=result.get("stderr")
        )
        
    except FgbioError as e:
        logger.error(f"fgbio error in filter_bam: {e}")
        return FilterBamResponse(
            success=False,
            message=f"fgbio error: {str(e)}",
            input_file=request.input_bam,
            output_file=request.output_bam,
            rejects_file=request.rejects,
            intervals_file=request.intervals,
            filters_applied={}
        )
    except Exception as e:
        logger.error(f"Unexpected error in filter_bam: {e}")
        return FilterBamResponse(
            success=False,
            message=f"Unexpected error: {str(e)}",
            input_file=request.input_bam,
            output_file=request.output_bam,
            rejects_file=request.rejects,
            intervals_file=request.intervals,
            filters_applied={}
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