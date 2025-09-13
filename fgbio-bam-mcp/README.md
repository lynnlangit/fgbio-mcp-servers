# fgbio BAM MCP Server

An MCP (Model Context Protocol) server that provides access to fgbio BAM manipulation tools through Claude. This server enables you to sort and filter BAM files using fgbio's powerful bioinformatics utilities directly from Claude conversations.

<img src="https://github.com/lynnlangit/fgbio-mcp-servers/blob/main/fgbio-bam-mcp/images/fgbio-mcp-server.png">

## Features

### Available Tools

#### SortBam
Sort BAM files using various sort orders:
- **coordinate** - Sort by genomic coordinates (default)
- **queryname** - Sort by read name
- **random** - Random order (deterministic)
- **unsorted** - No specific order

Parameters:
- `input_bam` - Path to input BAM file
- `output_bam` - Path for output BAM file
- `sort_order` - Sort order (default: coordinate)
- `temp_dir` - Optional temporary directory
- `max_records_in_ram` - Memory limit for sorting

#### FilterBam

Filter BAM files to remove unwanted reads:

**Default Filters:**
- Remove unmapped reads
- Remove duplicate reads
- Remove secondary alignments
- Remove reads with MAPQ < 1

**Optional Filters:**
- Insert size range filtering
- Minimum mapped bases requirement
- Single-end mapping removal
- Genomic interval filtering
- Custom mapping quality thresholds

Parameters:
- `input_bam` - Path to input BAM file
- `output_bam` - Path for filtered output BAM file
- `rejects` - Optional output file for rejected reads
- `intervals` - Optional intervals file for region filtering
- `remove_duplicates` - Remove duplicate reads (default: true)
- `remove_unmapped_reads` - Remove unmapped reads (default: true)
- `min_map_q` - Minimum mapping quality (default: 1)
- `remove_single_end_mappings` - Remove non-PE reads (default: false)
- `remove_secondary_alignments` - Remove secondary alignments (default: true)
- `min_insert_size` - Minimum insert size filter
- `max_insert_size` - Maximum insert size filter
- `min_mapped_bases` - Minimum mapped bases filter

## Prerequisites

- Python 3.9+
- [fgbio](https://github.com/fulcrumgenomics/fgbio) installed and available in PATH
  ```bash
  # Install via Homebrew (macOS)
  brew install fgbio
  
  # Or download from GitHub releases
  # https://github.com/fulcrumgenomics/fgbio/releases
  ```

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd fgbio-bam-mcp
   ```

2. Install in development mode:
   ```bash
   pip install -e .
   ```

3. Verify installation:
   ```bash
   fgbio-bam-mcp --help
   ```

## Usage with Claude

### Add to Claude MCP Configuration

```bash
claude mcp add fgbio-bam-mcp /path/to/fgbio-bam-mcp/src/fgbio_bam_mcp/server.py
```

### Using the Tools

Once configured, you can use the tools in Claude conversations:

**Sort a BAM file:**
```text
Please sort my BAM file input.bam by coordinate and save it as sorted.bam
```

**Filter a BAM file:**
```text
Filter my BAM file to remove duplicates and low-quality reads (MAPQ < 10), 
keeping only reads with insert sizes between 100-500bp
```

**Complex workflows:**
```text
First sort input.bam by queryname, then filter to remove duplicates, 
unmapped reads, and reads outside chr1:1000000-2000000
```

## Project Structure

```text
fgbio-bam-mcp/src/fgbio_bam_mcp/
__init__.py          # Package initialization
server.py            # FastMCP server w tool definitions
fgbio_wrapper.py     # fgbio command wrapper
pyproject.toml       # Project configuration
README.md            # This file
examples/            # Usage examples
```

## Development

### Key Components

- **FgbioWrapper** - Handles fgbio command execution, parameter validation, and error handling
- **Pydantic Models** - Type-safe request/response models with validation
- **FastMCP Tools** - MCP tool implementations with comprehensive error handling

### Adding New Tools

To add support for additional fgbio tools:

1. Add a method to `FgbioWrapper` class
2. Create Pydantic request/response models in `server.py`
3. Implement the MCP tool function with `@mcp.tool()` decorator
4. Add tests and documentation

### Error Handling

The server provides comprehensive error handling:
- File existence validation
- Path accessibility checks
- fgbio command validation
- Parameter validation
- Detailed error messages and logging

## Examples

### Basic BAM Sorting
```python
# Sort BAM by coordinates
response = sort_bam(SortBamRequest(
    input_bam="input.bam",
    output_bam="sorted.bam",
    sort_order="coordinate"
))
```

### Advanced BAM Filtering
```python
# Filter with multiple criteria
response = filter_bam(FilterBamRequest(
    input_bam="input.bam",
    output_bam="filtered.bam",
    rejects="rejected_reads.bam",
    min_map_q=20,
    min_insert_size=100,
    max_insert_size=500,
    remove_duplicates=True,
    remove_secondary_alignments=True
))
```

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## Support

For issues related to:

- **fgbio functionality**: See [fgbio documentation](https://github.com/fulcrumgenomics/fgbio)
- **MCP server**: Open an issue in this repository
- **Claude integration**: Check Claude MCP documentation
