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
                time, length, result_type, level = parser_func(log_path)
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


def calculate_average_time(times):
    """
    Calculate average solving time for all cases (including unsolved).
    Simply returns the mean of actual times.
    """
    return np.mean(times)


def calculate_average_time_above_threshold(times, threshold=100):
    """
    Calculate average solving time for cases where time > threshold.
    Includes timeout cases (3600s).
    """
    filtered_times = [t for t in times if t > threshold]
    if len(filtered_times) > 0:
        return np.mean(filtered_times)
    else:
        return None


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
    import argparse
    parser = argparse.ArgumentParser(description='Generate PAR-2 table')
    parser.add_argument('--ic3ref', action='store_true', help='Use IC3REF mode')
    parser.add_argument('--standard', type=str, help='Standard solver directory')
    parser.add_argument('--ctgdown', type=str, help='CtgDown solver directory')
    parser.add_argument('--dynamic', type=str, help='DynAMic solver directory (rIC3 only)')
    parser.add_argument('--mab', type=str, help='MAB solver directory')
    args = parser.parse_args()
    
    use_ic3ref = args.ic3ref
    
    # Configuration
    families = ['hwmcc20', 'hwmcc24', 'hwmcc2025']
    timeout = 3600
    thresholds = [1, 100, 200, 500, 1000]
    
    # Solver configurations
    if use_ic3ref:
        solvers = {
            'IC3REF-Standard': [args.standard] if args.standard else ['hpc_IC3REF_basic_20251219_redo'],
            'IC3REF-CtgDown': [args.ctgdown] if args.ctgdown else ['hpc_IC3REF_ctgdown_20251219_redo'],
            'IC3REF-MAB': [args.mab] if args.mab else ['hpc_IC3REF_mab_20251219_alpha_1_redo']
        }
        parser_func = parse_ic3ref_log
        solver_type = "IC3REF"
    else:
        solvers = {
            'rIC3-Standard': [args.standard] if args.standard else ['hpc_ric3_ic3_pure_20251221_redo'],
            'rIC3-CtgDown': [args.ctgdown] if args.ctgdown else ['hpc_ric3_ic3_ctgdown_20251221_redo'],
            'rIC3-DynAMic': [args.dynamic] if args.dynamic else ['hpc_ric3_dyn_20251221_redo'],
            'rIC3-DynAMic-MAB': [args.mab] if args.mab else ['hpc_ric3_ic3_mab_20251221_redo']
        }
        parser_func = parse_ric3_log
        solver_type = "rIC3"
    
    print("Loading family information...")
    family_basenames = get_family_basenames(families)
    print(f"Total benchmarks in families: {len(family_basenames)}\n")
    
    # Get individual family basenames
    family_basenames_individual = {}
    for family in families:
        family_basenames_individual[family] = get_family_basenames([family])
    
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
    print("=" * 140)
    print(f"PAR-2 Score Table for {solver_type} Variants on hwmcc20+24+25")
    print("=" * 140)
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
        
        # Count safe (proof) and unsafe (counter-example) separately
        safe_count = 0
        unsafe_count = 0
        for b in family_basenames:
            if b in results:
                time, length, result_type = results[b]
                if time < timeout:
                    if result_type == 'proof':
                        safe_count += 1
                    elif result_type == 'counter-example':
                        unsafe_count += 1
        stats[solver_name]['safe'] = safe_count
        stats[solver_name]['unsafe'] = unsafe_count
        
        stats[solver_name]['all'] = calculate_par2(times_all, timeout)
        stats[solver_name]['avg_time'] = calculate_average_time(times_all)
        stats[solver_name]['avg_time_100'] = calculate_average_time_above_threshold(times_all, 100)
        
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
    baseline_safe = stats[baseline_name]['safe']
    baseline_unsafe = stats[baseline_name]['unsafe']
    for solver_name in solver_names:
        stats[solver_name]['delta'] = stats[solver_name]['solved'] - baseline_solved
        stats[solver_name]['delta_safe'] = stats[solver_name]['safe'] - baseline_safe
        stats[solver_name]['delta_unsafe'] = stats[solver_name]['unsafe'] - baseline_unsafe
    
    # Print unified table
    header = f"{'Solver':<20} {'Solved':<10} {'Safe':<8} {'Unsafe':<8} {'Δ':<8} {'Δs':<6} {'Δu':<6} {'All':<12} {'Avg':<12} {'Avg>100':<12}"
    for threshold in thresholds:
        header += f" {'>' + str(threshold) + 's':<12}"
    print(header)
    print("-" * 164)
    
    for solver_name in solver_names:
        delta_str = f"+{stats[solver_name]['delta']}" if stats[solver_name]['delta'] > 0 else str(stats[solver_name]['delta'])
        delta_safe_str = f"+{stats[solver_name]['delta_safe']}" if stats[solver_name]['delta_safe'] > 0 else str(stats[solver_name]['delta_safe'])
        delta_unsafe_str = f"+{stats[solver_name]['delta_unsafe']}" if stats[solver_name]['delta_unsafe'] > 0 else str(stats[solver_name]['delta_unsafe'])
        
        avg_time_100_str = f"{stats[solver_name]['avg_time_100']:.2f}" if stats[solver_name]['avg_time_100'] is not None else 'N/A'
        row = f"{solver_name:<20} {stats[solver_name]['solved']:<10} {stats[solver_name]['safe']:<8} {stats[solver_name]['unsafe']:<8} {delta_str:<8} {delta_safe_str:<6} {delta_unsafe_str:<6} {stats[solver_name]['all']:<12.2f} {stats[solver_name]['avg_time']:<12.2f} {avg_time_100_str:<12}"
        for threshold in thresholds:
            par2 = stats[solver_name][f'>{threshold}s']
            if par2 is not None:
                row += f" {par2:<12.2f}"
            else:
                row += f" {'N/A':<12}"
        print(row)
    
    print("=" * 164)
    
    # Generate per-family tables
    print("\n")
    
    # Add hwmcc24+25 combined table
    print("=" * 140)
    print(f"PAR-2 Score Table for {solver_type} Variants on hwmcc24+hwmcc2025")
    print("=" * 140)
    print()
    
    # Get combined cases for hwmcc24+25 (with overlap handling)
    hwmcc24_25_cases = family_basenames_individual['hwmcc24'] | family_basenames_individual['hwmcc2025']
    print(f"Total cases in hwmcc24+hwmcc2025: {len(hwmcc24_25_cases)}")
    print(f"  hwmcc24: {len(family_basenames_individual['hwmcc24'])} cases")
    print(f"  hwmcc2025: {len(family_basenames_individual['hwmcc2025'])} cases")
    print(f"  Overlap: {len(family_basenames_individual['hwmcc24'] & family_basenames_individual['hwmcc2025'])} cases")
    print()
    
    # Calculate statistics for hwmcc24+25
    hwmcc24_25_stats = {}
    for solver_name in solver_names:
        hwmcc24_25_stats[solver_name] = {}
        results = filtered_results[solver_name]
        
        # Overall stats
        times_all = np.array([results[b][0] for b in hwmcc24_25_cases if b in results])
        if len(times_all) > 0:
            hwmcc24_25_stats[solver_name]['solved'] = np.sum(times_all < timeout)
            hwmcc24_25_stats[solver_name]['all'] = calculate_par2(times_all, timeout)
            hwmcc24_25_stats[solver_name]['avg_time'] = calculate_average_time(times_all)
            hwmcc24_25_stats[solver_name]['avg_time_100'] = calculate_average_time_above_threshold(times_all, 100)
        else:
            hwmcc24_25_stats[solver_name]['solved'] = 0
            hwmcc24_25_stats[solver_name]['all'] = None
            hwmcc24_25_stats[solver_name]['avg_time'] = None
            hwmcc24_25_stats[solver_name]['avg_time_100'] = None
            hwmcc24_25_stats[solver_name]['avg_time'] = None
        
        # Count safe and unsafe
        safe_count = 0
        unsafe_count = 0
        for b in hwmcc24_25_cases:
            if b in results:
                time, length, result_type = results[b]
                if time < timeout:
                    if result_type == 'proof':
                        safe_count += 1
                    elif result_type == 'counter-example':
                        unsafe_count += 1
        hwmcc24_25_stats[solver_name]['safe'] = safe_count
        hwmcc24_25_stats[solver_name]['unsafe'] = unsafe_count
        
        # For each threshold
        for threshold in thresholds:
            cases_above = get_cases_above_threshold(all_results, hwmcc24_25_cases, threshold)
            times = np.array([results[b][0] for b in cases_above if b in results])
            if len(times) > 0:
                hwmcc24_25_stats[solver_name][f'>{threshold}s'] = calculate_par2(times, timeout)
            else:
                hwmcc24_25_stats[solver_name][f'>{threshold}s'] = None
    
    # Calculate delta for hwmcc24+25
    baseline_solved_24_25 = hwmcc24_25_stats[baseline_name]['solved']
    baseline_safe_24_25 = hwmcc24_25_stats[baseline_name]['safe']
    baseline_unsafe_24_25 = hwmcc24_25_stats[baseline_name]['unsafe']
    for solver_name in solver_names:
        hwmcc24_25_stats[solver_name]['delta'] = hwmcc24_25_stats[solver_name]['solved'] - baseline_solved_24_25
        hwmcc24_25_stats[solver_name]['delta_safe'] = hwmcc24_25_stats[solver_name]['safe'] - baseline_safe_24_25
        hwmcc24_25_stats[solver_name]['delta_unsafe'] = hwmcc24_25_stats[solver_name]['unsafe'] - baseline_unsafe_24_25
    
    # Print table for hwmcc24+25
    header = f"{'Solver':<20} {'Solved':<10} {'Safe':<8} {'Unsafe':<8} {'Δ':<8} {'Δs':<6} {'Δu':<6} {'All':<12} {'Avg':<12} {'Avg>100':<12}"
    for threshold in thresholds:
        header += f" {'>' + str(threshold) + 's':<12}"
    print(header)
    print("-" * 164)
    
    for solver_name in solver_names:
        delta_str = f"+{hwmcc24_25_stats[solver_name]['delta']}" if hwmcc24_25_stats[solver_name]['delta'] > 0 else str(hwmcc24_25_stats[solver_name]['delta'])
        delta_safe_str = f"+{hwmcc24_25_stats[solver_name]['delta_safe']}" if hwmcc24_25_stats[solver_name]['delta_safe'] > 0 else str(hwmcc24_25_stats[solver_name]['delta_safe'])
        delta_unsafe_str = f"+{hwmcc24_25_stats[solver_name]['delta_unsafe']}" if hwmcc24_25_stats[solver_name]['delta_unsafe'] > 0 else str(hwmcc24_25_stats[solver_name]['delta_unsafe'])
        solved = hwmcc24_25_stats[solver_name]['solved']
        safe = hwmcc24_25_stats[solver_name]['safe']
        unsafe = hwmcc24_25_stats[solver_name]['unsafe']
        par2_all = hwmcc24_25_stats[solver_name]['all']
        avg_time = hwmcc24_25_stats[solver_name]['avg_time']
        avg_time_100 = hwmcc24_25_stats[solver_name]['avg_time_100']
        
        if par2_all is not None and avg_time is not None:
            avg_time_100_str = f"{avg_time_100:.2f}" if avg_time_100 is not None else 'N/A'
            row = f"{solver_name:<20} {solved:<10} {safe:<8} {unsafe:<8} {delta_str:<8} {delta_safe_str:<6} {delta_unsafe_str:<6} {par2_all:<12.2f} {avg_time:<12.2f} {avg_time_100_str:<12}"
        else:
            row = f"{solver_name:<20} {solved:<10} {safe:<8} {unsafe:<8} {delta_str:<8} {delta_safe_str:<6} {delta_unsafe_str:<6} {'N/A':<12} {'N/A':<12} {'N/A':<12}"
        
        for threshold in thresholds:
            par2 = hwmcc24_25_stats[solver_name][f'>{threshold}s']
            if par2 is not None:
                row += f" {par2:<12.2f}"
            else:
                row += f" {'N/A':<12}"
        print(row)
    
    print("=" * 164)
    print()
    
    # Individual family tables
    for family in families:
        print("=" * 140)
        print(f"PAR-2 Score Table for {solver_type} Variants on {family}")
        print("=" * 140)
        print()
        
        family_cases = family_basenames_individual[family]
        
        # Calculate statistics for this family
        family_stats = {}
        for solver_name in solver_names:
            family_stats[solver_name] = {}
            results = filtered_results[solver_name]
            
            # Overall stats
            times_all = np.array([results[b][0] for b in family_cases if b in results])
            if len(times_all) > 0:
                family_stats[solver_name]['solved'] = np.sum(times_all < timeout)
                family_stats[solver_name]['all'] = calculate_par2(times_all, timeout)
                family_stats[solver_name]['avg_time'] = calculate_average_time(times_all)
                family_stats[solver_name]['avg_time_100'] = calculate_average_time_above_threshold(times_all, 100)
            else:
                family_stats[solver_name]['solved'] = 0
                family_stats[solver_name]['all'] = None
                family_stats[solver_name]['avg_time'] = None
                family_stats[solver_name]['avg_time_100'] = None
            
            # Count safe and unsafe
            safe_count = 0
            unsafe_count = 0
            for b in family_cases:
                if b in results:
                    time, length, result_type = results[b]
                    if time < timeout:
                        if result_type == 'proof':
                            safe_count += 1
                        elif result_type == 'counter-example':
                            unsafe_count += 1
            family_stats[solver_name]['safe'] = safe_count
            family_stats[solver_name]['unsafe'] = unsafe_count
            
            # For each threshold
            for threshold in thresholds:
                cases_above = get_cases_above_threshold(all_results, family_cases, threshold)
                times = np.array([results[b][0] for b in cases_above if b in results])
                if len(times) > 0:
                    family_stats[solver_name][f'>{threshold}s'] = calculate_par2(times, timeout)
                else:
                    family_stats[solver_name][f'>{threshold}s'] = None
        
        # Calculate delta for this family
        baseline_solved = family_stats[baseline_name]['solved']
        baseline_safe_family = family_stats[baseline_name]['safe']
        baseline_unsafe_family = family_stats[baseline_name]['unsafe']
        for solver_name in solver_names:
            family_stats[solver_name]['delta'] = family_stats[solver_name]['solved'] - baseline_solved
            family_stats[solver_name]['delta_safe'] = family_stats[solver_name]['safe'] - baseline_safe_family
            family_stats[solver_name]['delta_unsafe'] = family_stats[solver_name]['unsafe'] - baseline_unsafe_family
        
        # Print table for this family
        header = f"{'Solver':<20} {'Solved':<10} {'Safe':<8} {'Unsafe':<8} {'Δ':<8} {'Δs':<6} {'Δu':<6} {'All':<12} {'Avg':<12} {'Avg>100':<12}"
        for threshold in thresholds:
            header += f" {'>' + str(threshold) + 's':<12}"
        print(header)
        print("-" * 164)
        
        for solver_name in solver_names:
            delta_str = f"+{family_stats[solver_name]['delta']}" if family_stats[solver_name]['delta'] > 0 else str(family_stats[solver_name]['delta'])
            delta_safe_str = f"+{family_stats[solver_name]['delta_safe']}" if family_stats[solver_name]['delta_safe'] > 0 else str(family_stats[solver_name]['delta_safe'])
            delta_unsafe_str = f"+{family_stats[solver_name]['delta_unsafe']}" if family_stats[solver_name]['delta_unsafe'] > 0 else str(family_stats[solver_name]['delta_unsafe'])
            solved = family_stats[solver_name]['solved']
            safe = family_stats[solver_name]['safe']
            unsafe = family_stats[solver_name]['unsafe']
            par2_all = family_stats[solver_name]['all']
            avg_time = family_stats[solver_name]['avg_time']
            avg_time_100 = family_stats[solver_name]['avg_time_100']
            
            if par2_all is not None and avg_time is not None:
                avg_time_100_str = f"{avg_time_100:.2f}" if avg_time_100 is not None else 'N/A'
                row = f"{solver_name:<20} {solved:<10} {safe:<8} {unsafe:<8} {delta_str:<8} {delta_safe_str:<6} {delta_unsafe_str:<6} {par2_all:<12.2f} {avg_time:<12.2f} {avg_time_100_str:<12}"
            else:
                row = f"{solver_name:<20} {solved:<10} {safe:<8} {unsafe:<8} {delta_str:<8} {delta_safe_str:<6} {delta_unsafe_str:<6} {'N/A':<12} {'N/A':<12} {'N/A':<12}"
            
            for threshold in thresholds:
                par2 = family_stats[solver_name][f'>{threshold}s']
                if par2 is not None:
                    row += f" {par2:<12.2f}"
                else:
                    row += f" {'N/A':<12}"
            print(row)
        
        print("=" * 164)
        print()
    
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
