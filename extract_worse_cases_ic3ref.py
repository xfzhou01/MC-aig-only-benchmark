#!/usr/bin/env python3
"""
Extract cases where IC3Ref-MAB or IC3Ref-CtgDown solved fewer than IC3Ref-Standard (Basic)
and copy the corresponding .aig files to separate folders.

Usage:
    python extract_worse_cases_ic3ref.py [--debug]
    
    --debug: Only print which cases cannot be solved, without searching/copying files
"""

import os
import sys
import shutil
from pathlib import Path
from parse_ic3ref_log import parse_ic3ref_log
from parse_aig_list import parse_aig_list

# Configuration
WORKSPACE = Path(__file__).parent
TIMEOUT = 3600
DEBUG_MODE = '--debug' in sys.argv

# IC3REF solver configurations
IC3REF_SOLVERS = {
    'IC3REF-Standard': [
        WORKSPACE / 'hpc_IC3REF_basic_20251219_redo'
    ],
    'IC3REF-CtgDown': [
        WORKSPACE / 'hpc_IC3REF_ctgdown_20251219_redo'
    ],
    'IC3REF-MAB': [
        WORKSPACE / 'hpc_IC3REF_mab_20251219_alpha_1_redo'
    ]
}

# Family definitions
FAMILIES = {
    'hwmcc20': ['hwmcc20'],
    'hwmcc24': ['hwmcc24'],
    'hwmcc2025': ['hwmcc2025']
}

# AIG file locations
AIG_LOCATIONS = {
    'hwmcc20': WORKSPACE / 'hwmcc20',
    'hwmcc24': WORKSPACE / 'hwmcc24',
    'hwmcc2025': WORKSPACE / 'hwmcc2025'
}

def get_case_basename(log_file):
    """Extract case basename from log filename."""
    name = log_file.stem
    if name.endswith('_log'):
        name = name[:-4]
    return name

def load_solver_results(solver_name, solver_dirs):
    """Load all results for a solver."""
    results = {}  # basename -> (time, length, result_type)
    
    for solver_dir in solver_dirs:
        if not solver_dir.exists():
            print(f"Warning: Directory {solver_dir} does not exist")
            continue
        
        log_files = list(solver_dir.glob('*_log.txt'))
        print(f"  {solver_name}: Found {len(log_files)} logs in {solver_dir.name}")
        
        for log_file in log_files:
            basename = get_case_basename(log_file)
            
            try:
                time, length, result_type = parse_ic3ref_log(str(log_file))
                
                # Keep all results (will filter by time < timeout later)
                if basename not in results or time < results[basename][0]:
                    results[basename] = (time, length, result_type)
            except Exception as e:
                # Skip failed parses
                continue
    
    return results

def find_aig_file(basename, family):
    """Find the .aig file for a given case basename in the family."""
    # First try the known family location
    if family and family in AIG_LOCATIONS:
        family_dir = AIG_LOCATIONS[family]
        if family_dir.exists():
            # Search recursively for .aig file
            for aig_file in family_dir.rglob('*.aig'):
                if aig_file.stem == basename:
                    return aig_file
    
    # If not found or family unknown, search entire workspace
    print(f"    Searching workspace for {basename}...", end='', flush=True)
    for aig_file in WORKSPACE.rglob('*.aig'):
        if aig_file.stem == basename:
            print(f" found in {aig_file.parent.name}")
            return aig_file
    
    print(f" not found")
    return None

def main():
    print("="*80)
    if DEBUG_MODE:
        print("DEBUG MODE: Analyzing IC3Ref Cases (no file operations)")
    else:
        print("Extracting IC3Ref Cases Where MAB/CtgDown Perform Worse Than Standard")
    print("="*80)
    print()
    
    # Get hwmcc20+24+25 case list
    print("Loading hwmcc20+24+25 case list...")
    aig_files_by_family, _ = parse_aig_list('aig_files_list.txt')
    target_families = ['hwmcc20', 'hwmcc24', 'hwmcc2025']
    target_cases = set()
    for family in target_families:
        if family in aig_files_by_family:
            for basename in aig_files_by_family[family]:
                basename_clean = basename.replace('.aig', '')
                target_cases.add(basename_clean)
    print(f"  Found {len(target_cases)} cases in hwmcc20+24+25")
    print()
    
    # Load all solver results
    print("Loading solver results...")
    all_results = {}
    for solver_name, solver_dirs in IC3REF_SOLVERS.items():
        all_results[solver_name] = load_solver_results(solver_name, solver_dirs)
        print(f"  {solver_name}: {len(all_results[solver_name])} cases solved (all datasets)")
    print()
    
    # Filter to only target cases
    print("Filtering to hwmcc20+24+25 cases only...")
    filtered_results = {}
    for solver_name, results in all_results.items():
        filtered_results[solver_name] = {
            case: results[case] for case in results if case in target_cases
        }
        print(f"  {solver_name}: {len(filtered_results[solver_name])} logs in hwmcc20+24+25")
    
    # Find cases where each solver actually solved (time < timeout)
    standard_solved = set(case for case, (time, _, _) in filtered_results['IC3REF-Standard'].items() if time < TIMEOUT)
    ctgdown_solved = set(case for case, (time, _, _) in filtered_results['IC3REF-CtgDown'].items() if time < TIMEOUT)
    mab_solved = set(case for case, (time, _, _) in filtered_results['IC3REF-MAB'].items() if time < TIMEOUT)
    
    print(f"  IC3REF-Standard: {len(standard_solved)} cases solved (time < timeout)")
    print(f"  IC3REF-CtgDown: {len(ctgdown_solved)} cases solved (time < timeout)")
    print(f"  IC3REF-MAB: {len(mab_solved)} cases solved (time < timeout)")
    print()
    
    # Cases where Standard solved but CtgDown didn't
    ctgdown_worse = standard_solved - ctgdown_solved
    # Cases where CtgDown solved but Standard didn't
    ctgdown_better = ctgdown_solved - standard_solved
    
    # Cases where Standard solved but MAB didn't
    mab_worse = standard_solved - mab_solved
    # Cases where MAB solved but Standard didn't
    mab_better = mab_solved - standard_solved
    
    print(f"Cases solved by Standard but NOT by CtgDown: {len(ctgdown_worse)}")
    print(f"Cases solved by CtgDown but NOT by Standard: {len(ctgdown_better)}")
    print(f"Net difference (Standard - CtgDown): {len(ctgdown_worse) - len(ctgdown_better)}")
    print()
    print(f"Cases solved by Standard but NOT by MAB: {len(mab_worse)}")
    print(f"Cases solved by MAB but NOT by Standard: {len(mab_better)}")
    print(f"Net difference (Standard - MAB): {len(mab_worse) - len(mab_better)}")
    print()
    
    # Print the cases
    if ctgdown_worse:
        print("="*80)
        print("CtgDown worse cases (Standard solved, CtgDown didn't):")
        print("="*80)
        for i, case in enumerate(sorted(ctgdown_worse), 1):
            print(f"{i:4d}. {case}")
        print()
    
    if mab_worse:
        print("="*80)
        print("MAB worse cases (Standard solved, MAB didn't):")
        print("="*80)
        for i, case in enumerate(sorted(mab_worse), 1):
            print(f"{i:4d}. {case}")
        print()
    
    # If debug mode, stop here
    if DEBUG_MODE:
        print("="*80)
        print("DEBUG MODE: Stopping before file operations")
        print("="*80)
        return
    
    # Identify family for each case (check which family directory contains it)
    case_family = {}
    print("Identifying case families...")
    all_target_cases = ctgdown_worse | mab_worse
    for case in all_target_cases:
        for family_name, family_dir in AIG_LOCATIONS.items():
            if family_dir.exists():
                aig_file = find_aig_file(case, family_name)
                if aig_file:
                    case_family[case] = family_name
                    break
    print(f"  Identified {len(case_family)} cases with family information")
    print()
    
    # Create output directories
    output_base = WORKSPACE / 'ic3ref_worse_cases'
    ctgdown_dir = output_base / 'ctgdown_worse_than_basic'
    mab_dir = output_base / 'mab_worse_than_basic'
    
    ctgdown_dir.mkdir(parents=True, exist_ok=True)
    mab_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy CtgDown worse cases
    print("Copying CtgDown worse cases...")
    ctgdown_copied = 0
    ctgdown_not_found = []
    for case in sorted(ctgdown_worse):
        family = case_family.get(case)
        aig_file = find_aig_file(case, family)
        if aig_file and aig_file.exists():
            dest = ctgdown_dir / aig_file.name
            shutil.copy2(aig_file, dest)
            print(f"  ✓ {case} ({family if family else 'workspace'})")
            ctgdown_copied += 1
        else:
            ctgdown_not_found.append(case)
            print(f"  ✗ {case} (not found)")
    
    print(f"\nCtgDown: Copied {ctgdown_copied}/{len(ctgdown_worse)} files")
    if ctgdown_not_found:
        print(f"  Not found: {', '.join(ctgdown_not_found[:10])}" + 
              (f" and {len(ctgdown_not_found)-10} more..." if len(ctgdown_not_found) > 10 else ""))
    print()
    
    # Copy MAB worse cases
    print("Copying MAB worse cases...")
    mab_copied = 0
    mab_not_found = []
    for case in sorted(mab_worse):
        family = case_family.get(case)
        aig_file = find_aig_file(case, family)
        if aig_file and aig_file.exists():
            dest = mab_dir / aig_file.name
            shutil.copy2(aig_file, dest)
            print(f"  ✓ {case} ({family if family else 'workspace'})")
            mab_copied += 1
        else:
            mab_not_found.append(case)
            print(f"  ✗ {case} (not found)")
    
    print(f"\nMAB: Copied {mab_copied}/{len(mab_worse)} files")
    if mab_not_found:
        print(f"  Not found: {', '.join(mab_not_found[:10])}" + 
              (f" and {len(mab_not_found)-10} more..." if len(mab_not_found) > 10 else ""))
    print()
    
    # Summary
    print("="*80)
    print("Summary")
    print("="*80)
    print(f"CtgDown worse cases: {len(ctgdown_worse)} found, {ctgdown_copied} copied")
    print(f"  Output directory: {ctgdown_dir}")
    print(f"MAB worse cases: {len(mab_worse)} found, {mab_copied} copied")
    print(f"  Output directory: {mab_dir}")
    print()
    
    # Create a summary file
    summary_file = output_base / 'summary.txt'
    with open(summary_file, 'w') as f:
        f.write("IC3Ref Worse Cases Analysis\n")
        f.write("="*80 + "\n\n")
        f.write(f"Cases where Standard solved but CtgDown didn't: {len(ctgdown_worse)}\n")
        for case in sorted(ctgdown_worse):
            family = case_family.get(case, 'unknown')
            f.write(f"  - {case} ({family})\n")
        f.write(f"\nCases where Standard solved but MAB didn't: {len(mab_worse)}\n")
        for case in sorted(mab_worse):
            family = case_family.get(case, 'unknown')
            f.write(f"  - {case} ({family})\n")
    
    print(f"Summary written to: {summary_file}")

if __name__ == '__main__':
    main()
