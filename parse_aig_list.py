#!/usr/bin/env python3
"""
Script to parse the collected .aig file list and extract basenames.
Handles duplicate basenames from different datasets (which is expected).
"""

import os
from collections import defaultdict


def parse_aig_list(input_file):
    """
    Parse the .aig file list and extract basenames organized by dataset.
    
    Args:
        input_file: Path to the text file containing full paths to .aig files
        
    Returns:
        tuple: (dict mapping dataset to list of basenames, dict mapping basename to list of full paths)
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    dataset_to_basenames = defaultdict(list)
    basename_to_paths = defaultdict(list)
    current_dataset = None
    
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines, header lines, and separator lines
            if not line or line.startswith('Total:') or \
               line.startswith('=') or line.startswith('-'):
                continue
            
            # Check if this is a dataset header line like "[hwmcc08] - 428 files"
            if line.startswith('['):
                # Extract dataset name from "[datasetname] - N files"
                current_dataset = line.split(']')[0][1:]
                continue
            
            # Only process lines that contain actual file paths
            if not line.endswith('.aig'):
                continue
            
            # Extract basename (filename without path)
            basename = os.path.basename(line)
            
            # Add to dataset mapping
            if current_dataset:
                dataset_to_basenames[current_dataset].append(basename)
            
            # Keep the old mapping for backward compatibility
            basename_to_paths[basename].append(line)
    
    return dict(dataset_to_basenames), dict(basename_to_paths)


def get_unique_basenames(input_file):
    """
    Get unique basenames from the .aig file list.
    
    Args:
        input_file: Path to the text file containing full paths to .aig files
        
    Returns:
        set: Set of unique basenames
    """
    dataset_to_basenames, _ = parse_aig_list(input_file)
    all_basenames = []
    for basenames in dataset_to_basenames.values():
        all_basenames.extend(basenames)
    return set(all_basenames)


def get_basename_statistics(input_file):
    """
    Get statistics about basenames including duplicates across datasets.
    
    Args:
        input_file: Path to the text file containing full paths to .aig files
        
    Returns:
        dict: Statistics including total files, unique basenames, and duplicates
    """
    dataset_to_basenames, basename_to_paths = parse_aig_list(input_file)
    
    total_files = sum(len(basenames) for basenames in dataset_to_basenames.values())
    unique_basenames = len(basename_to_paths)
    duplicates = {name: paths for name, paths in basename_to_paths.items() if len(paths) > 1}
    
    stats = {
        'total_files': total_files,
        'unique_basenames': unique_basenames,
        'duplicate_count': len(duplicates),
        'duplicates': duplicates
    }
    
    return stats


def main():
    """
    Example usage of the parsing functions.
    """
    input_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aig_files_list.txt")
    
    print("Parsing .aig file list...")
    dataset_to_basenames, basename_to_paths = parse_aig_list(input_file)
    
    # Print dataset statistics
    print("\nDatasets and basename counts:")
    print("=" * 60)
    total_files = 0
    for dataset, basenames in sorted(dataset_to_basenames.items()):
        count = len(basenames)
        total_files += count
        print(f"{dataset:25s}: {count:4d} files")
    
    print("=" * 60)
    print(f"Total .aig files: {total_files}")
    print(f"Unique basenames: {len(basename_to_paths)}")
    
    # Get statistics
    stats = get_basename_statistics(input_file)
    print(f"\nDuplicate basenames: {stats['duplicate_count']}")
    
    if stats['duplicate_count'] > 0:
        print("\nExamples of duplicate basenames (first 5):")
        for i, (basename, paths) in enumerate(list(stats['duplicates'].items())[:5]):
            print(f"  {basename}: {len(paths)} occurrences")
            for path in paths:
                print(f"    - {path}")
    
    # Get unique basenames as a set
    unique = get_unique_basenames(input_file)
    print(f"\nUnique basenames set size: {len(unique)}")
    
    # Print the dataset_to_basenames dictionary (first 3 files per dataset)
    print("\n" + "=" * 60)
    print("Dataset to Basenames Dictionary (showing first 3 files):")
    print("=" * 60)
    for dataset, basenames in sorted(dataset_to_basenames.items()):
        print(f"\n'{dataset}': [")
        for i, basename in enumerate(basenames[:3]):
            print(f"    '{basename}',")
        if len(basenames) > 3:
            print(f"    ... ({len(basenames) - 3} more files)")
        print("]")


if __name__ == "__main__":
    main()
