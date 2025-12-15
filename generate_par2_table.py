#!/usr/bin/env python3
"""
Generate PAR-2 score table for rIC3 variants on hwmcc20+24+25.
Statistics include: solved count, PAR-2 scores for different time thresholds.

Usage:
    python generate_par2_table.py [--ic3ref]
    
    --ic3ref: Use IC3REF solvers instead of rIC3 solvers
"""

import os
import sys
import numpy as np
from parse_aig_list import parse_aig_list
from parse_ric3_log import parse_ric3_log
from parse_ic3ref_log import parse_ic3ref_log


def parse_log_directories(log_dirs, parser_func):
    """Parse all log files from multiple directories (merged)."""
    results = {}
    
    for log_dir in log_dirs:
        if not os.path.exists(log_dir):
            print(f"Warning: Directory not found: {log_dir}")
            continue
        
        for filename in os.listdir(log_dir):
            if not filename.endswith('_log.txt'):
                continue
            
            basename = filename.replace('_log.txt', '')
            log_path = os.path.join(log_dir, filename)
            
            try:
                time, length, result_type = parser_func(log_path)
                if basename not in results:
                    results[basename] = (time, length, result_type)
            except Exception as e:
                continue
    
    return results


def get_family_basenames(families, aig_list_file='aig_files_list.txt'):
    """Get all basenames for specified families."""
    aig_files_by_family, _ = parse_aig_list(aig_list_file)
    
    family_basenames = set()
    for family in families:
        if family in aig_files_by_family:
            for basename in aig_files_by_family[family]:
                basename_clean = basename.replace('.aig', '')
                family_basenames.add(basename_clean)
    
    return family_basenames


def calculate_par2(times, timeout=3600):
    """
    Calculate PAR-2 score.
    PAR-2 = average time, with timeout cases counted as 2*timeout
    """
    adjusted_times = []
    for t in times:
        if t >= timeout:
            adjusted_times.append(2 * timeout)
        else:
            adjusted_times.append(t)
    
    return np.mean(adjusted_times)


def get_cases_above_threshold(all_results, family_basenames, threshold):
    """
    Get cases where at least one solver takes more than threshold seconds.
    """
    cases_above = set()
    
    for basename in family_basenames:
        for results in all_results.values():
            if basename in results:
                time, _, _ = results[basename]
                if time > threshold:
                    cases_above.add(basename)
                    break
    
    return cases_above


def main():
    # Parse command line arguments
    use_ic3ref = '--ic3ref' in sys.argv
    
    # Configuration
    families = ['hwmcc20', 'hwmcc24', 'hwmcc2025']
    timeout = 3600
    thresholds = [1, 100, 200, 500, 1000]
    
    # Solver configurations
    if use_ic3ref:
        solvers = {
            'IC3REF-Standard': ['hpc_IC3REF_basic_new', 'hpc_IC3REF_basic_new_2025'],
            'IC3REF-CtgDown': ['hpc_IC3REF_ctg_new_2025', 'hpc_IC3REF_ctgdown'],
            'IC3REF-MAB': ['hpc_IC3REF_mab_context_po_len_and_delta', 'hpc_IC3REF_mab_new_2025']
        }
        parser_func = parse_ic3ref_log
        solver_type = "IC3REF"
    else:
        solvers = {
            'rIC3-Standard': ['hpc_ric3_ic3_pure', 'hpc_ric3_ic3_pure_2025'],
            'rIC3-CtgDown': ['hpc_ric3_ctg_2025', 'hpc_ric3_ctg'],
            'rIC3-DynAMic': ['hpc_ric3_dyn_2025', 'hpc_ric3_sl_dynamic'],
            'rIC3-DynAMic-MAB': ['hpc_ric3_mab_2025', 'hpc_ric3_sl_mab_6_add_context_and_reward_decay070']
        }
        parser_func = parse_ric3_log
        solver_type = "rIC3"
    
    print("Loading family information...")
    family_basenames = get_family_basenames(families)
    print(f"Total benchmarks in families: {len(family_basenames)}\n")
    
    # Parse all solver results
    print("Parsing solver logs...")
    all_results = {}
    for solver_name, dirs in solvers.items():
        print(f"  {solver_name}: ", end='')
        results = parse_log_directories(dirs, parser_func)
        all_results[solver_name] = results
        print(f"{len(results)} logs")
    print()
    
    # Filter to family basenames
    filtered_results = {}
    for solver_name, results in all_results.items():
        filtered = {k: v for k, v in results.items() if k in family_basenames}
        filtered_results[solver_name] = filtered
    
    # Generate table
    print("=" * 120)
    print(f"PAR-2 Score Table for {solver_type} Variants on hwmcc20+24+25")
    print("=" * 120)
    print()
    
    # Calculate all statistics first
    stats = {}
    solver_names = list(solvers.keys())
    
    for solver_name in solver_names:
        stats[solver_name] = {}
        results = filtered_results[solver_name]
        
        # Overall stats
        times_all = np.array([results[b][0] for b in family_basenames if b in results])
        stats[solver_name]['solved'] = np.sum(times_all < timeout)
        stats[solver_name]['all'] = calculate_par2(times_all, timeout)
        
        # For each threshold
        for threshold in thresholds:
            cases_above = get_cases_above_threshold(all_results, family_basenames, threshold)
            times = np.array([results[b][0] for b in cases_above if b in results])
            if len(times) > 0:
                stats[solver_name][f'>{threshold}s'] = calculate_par2(times, timeout)
            else:
                stats[solver_name][f'>{threshold}s'] = None
    
    # Calculate delta (difference from Standard)
    baseline_name = f'{solver_type}-Standard'
    baseline_solved = stats[baseline_name]['solved']
    for solver_name in solver_names:
        stats[solver_name]['delta'] = stats[solver_name]['solved'] - baseline_solved
    
    # Print unified table
    header = f"{'Solver':<20} {'Solved':<10} {'Δ':<8} {'All':<12}"
    for threshold in thresholds:
        header += f" {'>' + str(threshold) + 's':<12}"
    print(header)
    print("-" * 120)
    
    for solver_name in solver_names:
        delta_str = f"+{stats[solver_name]['delta']}" if stats[solver_name]['delta'] > 0 else str(stats[solver_name]['delta'])
        row = f"{solver_name:<20} {stats[solver_name]['solved']:<10} {delta_str:<8} {stats[solver_name]['all']:<12.2f}"
        for threshold in thresholds:
            par2 = stats[solver_name][f'>{threshold}s']
            if par2 is not None:
                row += f" {par2:<12.2f}"
            else:
                row += f" {'N/A':<12}"
        print(row)
    
    print("=" * 120)
    
    # Generate CSV output
    csv_file = f'par2_scores_hwmcc20_24_25_{solver_type.lower()}.csv'
    with open(csv_file, 'w') as f:
        # Header
        f.write("Solver,Threshold,Cases,Solved,PAR-2\n")
        
        # All cases
        for solver_name in solvers.keys():
            results = filtered_results[solver_name]
            times = np.array([results[b][0] for b in family_basenames if b in results])
            solved_count = np.sum(times < timeout)
            par2_score = calculate_par2(times, timeout)
            
            f.write(f"{solver_name},All,{len(family_basenames)},{solved_count},{par2_score:.2f}\n")
        
        # For each threshold
        for threshold in thresholds:
            cases_above = get_cases_above_threshold(all_results, family_basenames, threshold)
            
            for solver_name in solvers.keys():
                results = filtered_results[solver_name]
                times = np.array([results[b][0] for b in cases_above if b in results])
                
                if len(times) > 0:
                    solved_count = np.sum(times < timeout)
                    par2_score = calculate_par2(times, timeout)
                    f.write(f"{solver_name},>{threshold}s,{len(cases_above)},{solved_count},{par2_score:.2f}\n")
    
    print(f"\nCSV file saved to: {csv_file}")


if __name__ == '__main__':
    main()
