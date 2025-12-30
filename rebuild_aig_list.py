#!/usr/bin/env python3
"""
Rebuild aig_files_list.txt based on the actual directory structure.
This script scans the three benchmark directories and creates a properly formatted list.
"""

import os
from pathlib import Path
from collections import defaultdict


def scan_directory(directory, family_name):
    """Scan a directory recursively for .aig files."""
    aig_files = []
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"Warning: Directory not found: {directory}")
        return aig_files
    
    print(f"Scanning {family_name}: {directory}")
    
    for aig_file in dir_path.rglob('*.aig'):
        aig_files.append(str(aig_file))
    
    print(f"  Found {len(aig_files)} .aig files")
    return aig_files


def main():
    # Define the three benchmark directories
    benchmark_dirs = {
        'hwmcc20': '/home/x/xiaofeng-zhou/hwmcc20',
        'hwmcc24': '/home/x/xiaofeng-zhou/benchmarks_2024',
        'hwmcc2025': '/home/x/xiaofeng-zhou/MC-aig-only-benchmark/hwmcc2025'
    }
    
    output_file = 'aig_files_list.txt'
    
    print("="*80)
    print("Rebuilding aig_files_list.txt")
    print("="*80)
    print()
    
    # Collect files from each directory
    all_files_by_family = {}
    total_files = 0
    
    for family_name, directory in benchmark_dirs.items():
        files = scan_directory(directory, family_name)
        all_files_by_family[family_name] = sorted(files)
        total_files += len(files)
    
    print()
    print("="*80)
    print("Writing results to", output_file)
    print("="*80)
    
    # Write to output file
    with open(output_file, 'w') as f:
        f.write("Collected .aig files from hwmcc20, hwmcc24, and hwmcc2025\n")
        f.write("="*80 + "\n\n")
        
        for family_name in ['hwmcc20', 'hwmcc24', 'hwmcc2025']:
            files = all_files_by_family[family_name]
            f.write(f"[{family_name}] - {len(files)} files\n")
            f.write("-"*80 + "\n")
            for file_path in files:
                f.write(f"{file_path}\n")
            f.write("\n")
        
        f.write("="*80 + "\n")
        f.write(f"Total: {total_files} .aig files\n")
        f.write("="*80 + "\n")
    
    print(f"\nTotal {total_files} .aig files written to {output_file}")
    print()
    
    # Print summary
    print("Summary by family:")
    for family_name in ['hwmcc20', 'hwmcc24', 'hwmcc2025']:
        print(f"  {family_name}: {len(all_files_by_family[family_name])} files")
    
    # Check for duplicates
    print("\nChecking for duplicate basenames across families...")
    basename_to_families = defaultdict(list)
    
    for family_name, files in all_files_by_family.items():
        for file_path in files:
            basename = os.path.basename(file_path)
            basename_to_families[basename].append(family_name)
    
    duplicates = {name: families for name, families in basename_to_families.items() if len(families) > 1}
    
    if duplicates:
        print(f"  Found {len(duplicates)} duplicate basenames across families:")
        for basename, families in sorted(duplicates.items())[:20]:  # Show first 20
            print(f"    {basename}: {', '.join(families)}")
        if len(duplicates) > 20:
            print(f"    ... and {len(duplicates) - 20} more")
    else:
        print("  No duplicate basenames found")


if __name__ == '__main__':
    main()
