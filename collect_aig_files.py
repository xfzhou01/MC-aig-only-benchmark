#!/usr/bin/env python3
"""
Script to collect all .aig filenames from specified benchmark directories.
Outputs the full paths to a text file for further processing.
"""

import os
from pathlib import Path


def collect_aig_files(base_dir, output_file):
    """
    Scan specified benchmark directories and collect all .aig file paths.
    
    Args:
        base_dir: Base directory containing benchmark folders
        output_file: Output text file path to write results
    """
    # Target directories to scan
    target_dirs = [
        "hwmcc08",
        "hwmcc11",
        "hwmcc13",
        "hwmcc15",
        "hwmcc19",
        "hwmcc20",
        "hwmcc24",
        "hwmcc2025",
        "LMCS-2006",
        "NuSMV-2.6-examples",
        "x-epic-2024"
    ]
    
    aig_files = []
    
    # Scan each target directory
    for target_dir in target_dirs:
        dir_path = os.path.join(base_dir, target_dir)
        
        if not os.path.exists(dir_path):
            print(f"Warning: Directory not found: {dir_path}")
            continue
        
        print(f"Scanning: {target_dir}")
        
        # Recursively find all .aig files
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.aig'):
                    full_path = os.path.join(root, file)
                    aig_files.append(full_path)
        
        print(f"  Found {len([f for f in aig_files if target_dir in f])} .aig files")
    
    # Organize files by directory
    files_by_dir = {}
    for aig_file in aig_files:
        for target_dir in target_dirs:
            if f"/{target_dir}/" in aig_file:
                if target_dir not in files_by_dir:
                    files_by_dir[target_dir] = []
                files_by_dir[target_dir].append(aig_file)
                break
    
    # Write results to output file with classification
    with open(output_file, 'w') as f:
        f.write(f"Total: {len(aig_files)} .aig files\n")
        f.write("=" * 80 + "\n\n")
        
        for target_dir in target_dirs:
            if target_dir in files_by_dir:
                files = sorted(files_by_dir[target_dir])
                f.write(f"[{target_dir}] - {len(files)} files\n")
                f.write("-" * 80 + "\n")
                for aig_file in files:
                    f.write(f"{aig_file}\n")
                f.write("\n")
    
    print(f"\nTotal: {len(aig_files)} .aig files collected")
    print(f"Results written to: {output_file}")


if __name__ == "__main__":
    # Base directory is the current directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(base_dir, "aig_files_list.txt")
    
    collect_aig_files(base_dir, output_file)
