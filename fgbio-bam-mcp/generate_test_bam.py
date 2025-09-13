#!/usr/bin/env python3
"""Generate a synthetic BAM file for testing fgbio tools."""

import pysam
import random
import os
from pathlib import Path

def generate_synthetic_bam(output_path: str, num_reads: int = 1000):
    """Generate a synthetic BAM file with realistic read data.
    
    Args:
        output_path: Path where the BAM file will be written
        num_reads: Number of read pairs to generate
    """
    print(f"Generating synthetic BAM file with {num_reads} read pairs...")
    
    # Define reference sequences (chromosomes)
    header = {
        'HD': {'VN': '1.6', 'SO': 'coordinate'},
        'SQ': [
            {'LN': 248956422, 'SN': 'chr1'},
            {'LN': 242193529, 'SN': 'chr2'},
            {'LN': 198295559, 'SN': 'chr3'},
            {'LN': 190214555, 'SN': 'chr4'},
            {'LN': 181538259, 'SN': 'chr5'},
        ],
        'RG': [
            {
                'ID': 'test_sample',
                'SM': 'synthetic_sample',
                'LB': 'test_library',
                'PL': 'ILLUMINA',
                'PU': 'test_flowcell.1.test_lane'
            }
        ],
        'PG': [
            {
                'ID': 'test_generator',
                'PN': 'generate_test_bam.py',
                'VN': '1.0'
            }
        ]
    }
    
    # Quality scores for realistic reads
    def generate_quality_string(length: int) -> str:
        """Generate realistic quality scores."""
        # Most bases high quality (30-40), some medium (20-29), few low (10-19)
        qualities = []
        for _ in range(length):
            rand = random.random()
            if rand < 0.7:  # 70% high quality
                qual = random.randint(30, 40)
            elif rand < 0.9:  # 20% medium quality  
                qual = random.randint(20, 29)
            else:  # 10% lower quality
                qual = random.randint(10, 19)
            qualities.append(chr(qual + 33))  # Convert to ASCII
        return ''.join(qualities)
    
    def generate_sequence(length: int) -> str:
        """Generate a random DNA sequence."""
        bases = ['A', 'T', 'G', 'C']
        return ''.join(random.choice(bases) for _ in range(length))
    
    # Generate all reads first, then sort by coordinate
    all_reads = []
    read_names = set()  # Track read names to ensure uniqueness
    
    print("Generating reads...")
    for i in range(num_reads):
            # Generate unique read name
            while True:
                read_name = f"read_{i:06d}"
                if read_name not in read_names:
                    read_names.add(read_name)
                    break
                i += 1
            
            # Choose random chromosome
            chrom_idx = random.randint(0, 4)
            chrom_name = f"chr{chrom_idx + 1}"
            chrom_length = header['SQ'][chrom_idx]['LN']
            
            # Read parameters
            read_length = random.choice([75, 100, 150])  # Common read lengths
            insert_size = random.randint(200, 800)  # Typical insert size range
            
            # Position for read 1 (ensure room for insert)
            max_pos = chrom_length - insert_size - read_length
            if max_pos < 1:
                max_pos = chrom_length // 2
            pos1 = random.randint(1, max_pos)
            pos2 = pos1 + insert_size - read_length
            
            # Generate sequences and qualities
            seq1 = generate_sequence(read_length)
            seq2 = generate_sequence(read_length)
            qual1 = generate_quality_string(read_length)
            qual2 = generate_quality_string(read_length)
            
            # Simulate some mapping quality variation
            mapq = random.choices([0, 1, 10, 20, 30, 40, 60], 
                                weights=[5, 5, 10, 15, 25, 25, 15])[0]
            
            # Create read 1
            read1 = pysam.AlignedSegment()
            read1.query_name = read_name
            read1.query_sequence = seq1
            read1.query_qualities = pysam.qualitystring_to_array(qual1)
            read1.flag = 99  # Paired, first in pair, mate reverse strand
            read1.reference_id = chrom_idx
            read1.reference_start = pos1 - 1  # 0-based
            read1.mapping_quality = mapq
            read1.cigar = [(0, read_length)]  # All matches
            read1.next_reference_id = chrom_idx
            read1.next_reference_start = pos2 - 1
            read1.template_length = insert_size
            read1.tags = [('RG', 'test_sample'), ('AS', read_length - random.randint(0, 5))]
            
            # Simulate some duplicates (5% chance)
            if random.random() < 0.05:
                read1.flag |= 1024  # Mark as duplicate
            
            # Create read 2  
            read2 = pysam.AlignedSegment()
            read2.query_name = read_name
            read2.query_sequence = seq2
            read2.query_qualities = pysam.qualitystring_to_array(qual2)
            read2.flag = 147  # Paired, second in pair, reverse strand
            read2.reference_id = chrom_idx
            read2.reference_start = pos2 - 1
            read2.mapping_quality = mapq
            read2.cigar = [(0, read_length)]  # All matches
            read2.next_reference_id = chrom_idx
            read2.next_reference_start = pos1 - 1
            read2.template_length = -insert_size
            read2.tags = [('RG', 'test_sample'), ('AS', read_length - random.randint(0, 5))]
            
            # Copy duplicate flag to mate
            if read1.flag & 1024:
                read2.flag |= 1024
            
            # Simulate some unmapped reads (2% chance)
            if random.random() < 0.02:
                read1.flag |= 4  # Unmapped
                read1.reference_id = -1
                read1.reference_start = -1
                read1.mapping_quality = 0
                read1.cigar = None
            
            if random.random() < 0.02:
                read2.flag |= 4  # Unmapped  
                read2.reference_id = -1
                read2.reference_start = -1
                read2.mapping_quality = 0
                read2.cigar = None
            
            # Simulate some secondary alignments (1% chance)
            if random.random() < 0.01:
                read1_secondary = pysam.AlignedSegment()
                read1_secondary.query_name = read_name
                read1_secondary.query_sequence = seq1
                read1_secondary.query_qualities = pysam.qualitystring_to_array(qual1)
                read1_secondary.flag = 355  # Secondary alignment
                read1_secondary.reference_id = random.randint(0, 4)
                read1_secondary.reference_start = random.randint(1, 1000000)
                read1_secondary.mapping_quality = random.randint(0, 20)
                read1_secondary.cigar = [(0, read_length)]
                read1_secondary.tags = [('RG', 'test_sample')]
                all_reads.append(read1_secondary)
            
            # Add reads to list
            all_reads.append(read1)
            all_reads.append(read2)
    
    # Sort reads by coordinate
    print("Sorting reads by coordinate...")
    all_reads.sort(key=lambda r: (r.reference_id if r.reference_id >= 0 else 999, 
                                  r.reference_start if r.reference_start >= 0 else 0))
    
    # Write sorted BAM file
    print("Writing sorted BAM file...")
    with pysam.AlignmentFile(output_path, "wb", header=header) as outfile:
        for read in all_reads:
            outfile.write(read)
    
    print(f"✓ Generated BAM file: {output_path}")
    
    # Index the BAM file
    print("Creating BAM index...")
    pysam.index(output_path)
    print(f"✓ Created index: {output_path}.bai")
    
    # Print file statistics
    with pysam.AlignmentFile(output_path, "rb") as bamfile:
        total_reads = 0
        mapped_reads = 0
        duplicate_reads = 0
        secondary_reads = 0
        
        for read in bamfile:
            total_reads += 1
            if not (read.flag & 4):  # Not unmapped
                mapped_reads += 1
            if read.flag & 1024:  # Duplicate
                duplicate_reads += 1
            if read.flag & 256:  # Secondary
                secondary_reads += 1
        
        print(f"✓ BAM file stats:")
        print(f"  Total reads: {total_reads}")
        print(f"  Mapped reads: {mapped_reads}")
        print(f"  Unmapped reads: {total_reads - mapped_reads}")
        print(f"  Duplicate reads: {duplicate_reads}")
        print(f"  Secondary alignments: {secondary_reads}")

if __name__ == "__main__":
    # Generate the test BAM file at the project root
    output_file = "test_sample.bam"
    generate_synthetic_bam(output_file, num_reads=5000)
    print(f"\n🎉 Synthetic BAM file generated successfully!")
    print(f"Use this file to test the fgbio MCP tools:")
    print(f"  File: {os.path.abspath(output_file)}")
    print(f"  Size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")