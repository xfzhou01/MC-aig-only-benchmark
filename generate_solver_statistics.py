#!/usr/bin/env python3
"""
Generate statistics table for solver performance across different families.
Shows how many safe/unsafe/unknown cases each solver solved in each family.

Usage:
    python generate_solver_statistics.py <log_dir1> <log_dir2> [parser_type]
    
    log_dir1: First solver log directory
    log_dir2: Second solver log directory
    parser_type: 'ric3' or 'ic3ref' (default: 'ric3')
    
Example:
    python generate_solver_statistics.py hpc_ric3_dyn_2025 hpc_ric3_mab_2025
    python generate_solver_statistics.py hpc_IC3REF_solver1 hpc_IC3REF_solver2 ic3ref
"""

import os
import sys
from collections import defaultdict
from parse_aig_list import parse_aig_list
from parse_ric3_log import parse_ric3_log
from parse_ic3ref_log import parse_ic3ref_log


def collect_solver_statistics(aig_dict, log_dir, parser_func):
    """
    Collect statistics for a solver across all families.
    
    Args:
        aig_dict: Dictionary mapping family to list of basenames
        log_dir: Path to solver log directory
        parser_func: Parser function (parse_ric3_log or parse_ic3ref_log)
        
    Returns:
        tuple: (family_stats, all_results)
            family_stats: dict {family: {'safe': count, 'unsafe': count, 'unknown': count, 'total': count}}
            all_results: dict {basename: result_type} for overall statistics
    """
    # Parse all logs once
    print(f"Parsing logs in {log_dir}...")
    results = {}
    
    if not os.path.exists(log_dir):
        print(f"Error: Directory not found: {log_dir}")
        return {}, {}
    
    for filename in os.listdir(log_dir):
        if not filename.endswith('_log.txt'):
            continue
        
        basename = filename.replace('_log.txt', '')
        log_path = os.path.join(log_dir, filename)
        
        try:
            time, length, result_type = parser_func(log_path)
            results[basename] = result_type
        except Exception as e:
            continue
    
    print(f"  Parsed {len(results)} logs")
    
    # Collect statistics per family
    stats = {}
    
    for family, benchmarks in sorted(aig_dict.items()):
        safe_count = 0
        unsafe_count = 0
        unknown_count = 0
        matched_count = 0  # Count only benchmarks that have log files
        
        for aig_file in benchmarks:
            basename = os.path.splitext(aig_file)[0]
            
            if basename in results:
                matched_count += 1
                result_type = results[basename]
                if result_type == 'proof':
                    safe_count += 1
                elif result_type == 'counter-example':
                    unsafe_count += 1
                elif result_type == 'unknown':
                    unknown_count += 1
        
        # Only add families that have at least one matching log file
        if matched_count > 0:
            stats[family] = {
                'safe': safe_count,
                'unsafe': unsafe_count,
                'unknown': unknown_count,
                'total': matched_count,  # Use matched count instead of all benchmarks
                'solved': safe_count + unsafe_count
            }
    
    return stats, results  # Return both per-family stats and all results


def print_statistics_table(stats_dict, solver_names, all_results_dict):
    """
    Print statistics table in a formatted way.
    
    Args:
        stats_dict: {solver_name: {family: {'safe': ..., 'unsafe': ..., ...}}}
        solver_names: List of solver names in order
        all_results_dict: {solver_name: {basename: result_type}} for overall unique stats
    """
    families = sorted(list(stats_dict[solver_names[0]].keys()))
    
    # Print header
    print("\n" + "="*120)
    print("Solver Performance Statistics by Family")
    print("="*120)
    
    for solver_name in solver_names:
        print(f"\n{solver_name}:")
        print("-"*120)
        print(f"{'Family':<20} {'Total':>8} {'Safe':>8} {'Unsafe':>8} {'Unknown':>8} {'Solved':>8} {'Solve%':>8}")
        print("-"*120)
        
        stats = stats_dict[solver_name]
        total_safe = 0
        total_unsafe = 0
        total_unknown = 0
        total_benchmarks = 0
        total_solved = 0
        
        for family in families:
            fam_stats = stats[family]
            safe = fam_stats['safe']
            unsafe = fam_stats['unsafe']
            unknown = fam_stats['unknown']
            total = fam_stats['total']
            solved = fam_stats['solved']
            solve_pct = (solved / total * 100) if total > 0 else 0
            
            print(f"{family:<20} {total:>8} {safe:>8} {unsafe:>8} {unknown:>8} {solved:>8} {solve_pct:>7.1f}%")
            
            total_safe += safe
            total_unsafe += unsafe
            total_unknown += unknown
            total_benchmarks += total
            total_solved += solved
        print("-"*120)
        
        # Calculate overall statistics from unique basenames (not sum of families)
        all_results = all_results_dict[solver_name]
        overall_safe = sum(1 for r in all_results.values() if r == 'proof')
        overall_unsafe = sum(1 for r in all_results.values() if r == 'counter-example')
        overall_unknown = sum(1 for r in all_results.values() if r == 'unknown')
        overall_total = len(all_results)
        overall_solved = overall_safe + overall_unsafe
        overall_solve_pct = (overall_solved / overall_total * 100) if overall_total > 0 else 0
        
        print(f"{'TOTAL (unique)':<20} {overall_total:>8} {overall_safe:>8} {overall_unsafe:>8} {overall_unknown:>8} {overall_solved:>8} {overall_solve_pct:>7.1f}%")
        print("-"*120)


def generate_csv_table(stats_dict, solver_names, all_results_dict, output_file):
    """
    Generate CSV file with statistics.
    
    Args:
        stats_dict: {solver_name: {family: {'safe': ..., 'unsafe': ..., ...}}}
        solver_names: List of solver names
        all_results_dict: {solver_name: {basename: result_type}} for overall unique stats
        output_file: Output CSV filename
    """
    families = sorted(list(stats_dict[solver_names[0]].keys()))
    
    with open(output_file, 'w') as f:
        # Write header
        f.write("Solver,Family,Total,Safe,Unsafe,Unknown,Solved,Solve%\n")
        
        for solver_name in solver_names:
            stats = stats_dict[solver_name]
            
            for family in families:
                fam_stats = stats[family]
                safe = fam_stats['safe']
                unsafe = fam_stats['unsafe']
                unknown = fam_stats['unknown']
                total = fam_stats['total']
                solved = fam_stats['solved']
                solve_pct = (solved / total * 100) if total > 0 else 0
                
                f.write(f"{solver_name},{family},{total},{safe},{unsafe},{unknown},{solved},{solve_pct:.1f}\n")
            
            # Write total row based on unique basenames
            all_results = all_results_dict[solver_name]
            overall_safe = sum(1 for r in all_results.values() if r == 'proof')
            overall_unsafe = sum(1 for r in all_results.values() if r == 'counter-example')
            overall_unknown = sum(1 for r in all_results.values() if r == 'unknown')
            overall_total = len(all_results)
            overall_solved = overall_safe + overall_unsafe
            overall_solve_pct = (overall_solved / overall_total * 100) if overall_total > 0 else 0
            
            f.write(f"{solver_name},TOTAL,{overall_total},{overall_safe},{overall_unsafe},{overall_unknown},{overall_solved},{overall_solve_pct:.1f}\n")
    
    print(f"\n✓ CSV table saved to: {output_file}")
def generate_family_comparison_tables(stats_dict, solver_names, all_results_dict, output_dir):
    """
    Generate comparison tables for each family and save to text file.
    
    Args:
        stats_dict: {solver_name: {family: {'safe': ..., 'unsafe': ..., ...}}}
        solver_names: List of solver names (should be 2 for comparison)
        all_results_dict: {solver_name: {basename: result_type}} for overall unique stats
        output_dir: Directory to save the text file
    """
    families = sorted(list(stats_dict[solver_names[0]].keys()))
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file = os.path.join(output_dir, "family_comparison.txt")
    
    with open(output_file, 'w') as f:
        f.write("="*100 + "\n")
        f.write("Solver Comparison by Family\n")
        f.write("="*100 + "\n\n")
        
        solver1_name = solver_names[0].replace('hpc_ric3_sl_', 'rIC3-').replace('_', ' ')
        solver2_name = solver_names[1].replace('hpc_ric3_sl_', 'rIC3-').replace('_', ' ')
        
        f.write(f"Solver 1: {solver1_name}\n")
        f.write(f"Solver 2: {solver2_name}\n\n")
        
        for family in families:
            stats1 = stats_dict[solver_names[0]][family]
            stats2 = stats_dict[solver_names[1]][family]
            
            f.write("-"*100 + "\n")
            f.write(f"Family: {family}\n")
            f.write("-"*100 + "\n\n")
            
            # Header
            f.write(f"{'Solver':<40} {'Total':>8} {'Safe':>8} {'Unsafe':>8} {'Unknown':>8} {'Solved':>8} {'Solve%':>8}\n")
            f.write("-"*100 + "\n")
            
            # Solver 1
            solve_pct1 = (stats1['solved'] / stats1['total'] * 100) if stats1['total'] > 0 else 0
            f.write(f"{solver1_name:<40} {stats1['total']:>8} {stats1['safe']:>8} {stats1['unsafe']:>8} "
                   f"{stats1['unknown']:>8} {stats1['solved']:>8} {solve_pct1:>7.1f}%\n")
            
            # Solver 2
            solve_pct2 = (stats2['solved'] / stats2['total'] * 100) if stats2['total'] > 0 else 0
            f.write(f"{solver2_name:<40} {stats2['total']:>8} {stats2['safe']:>8} {stats2['unsafe']:>8} "
                   f"{stats2['unknown']:>8} {stats2['solved']:>8} {solve_pct2:>7.1f}%\n")
            
            f.write("-"*100 + "\n")
            
            # Difference row
            safe_diff = stats2['safe'] - stats1['safe']
            unsafe_diff = stats2['unsafe'] - stats1['unsafe']
            unknown_diff = stats2['unknown'] - stats1['unknown']
            solved_diff = stats2['solved'] - stats1['solved']
            pct_diff = solve_pct2 - solve_pct1
            
            diff_line = f"{'Difference (Solver 2 - Solver 1)':<40} {0:>8} "
            diff_line += f"{safe_diff:>+8} {unsafe_diff:>+8} {unknown_diff:>+8} {solved_diff:>+8} {pct_diff:>+7.1f}%\n"
            f.write(diff_line)
            
            f.write("\n\n")
        f.write("Overall Summary (unique benchmarks only)\n")
        f.write("="*100 + "\n\n")
        
        # Calculate from unique basenames, not sum of families (due to overlap)
        all_results1 = all_results_dict[solver_names[0]]
        all_results2 = all_results_dict[solver_names[1]]
        
        total_stats1 = {
            'total': len(all_results1),
            'safe': sum(1 for r in all_results1.values() if r == 'proof'),
            'unsafe': sum(1 for r in all_results1.values() if r == 'counter-example'),
            'unknown': sum(1 for r in all_results1.values() if r == 'unknown'),
            'solved': sum(1 for r in all_results1.values() if r in ['proof', 'counter-example'])
        }
        
        total_stats2 = {
            'total': len(all_results2),
            'safe': sum(1 for r in all_results2.values() if r == 'proof'),
            'unsafe': sum(1 for r in all_results2.values() if r == 'counter-example'),
            'unknown': sum(1 for r in all_results2.values() if r == 'unknown'),
            'solved': sum(1 for r in all_results2.values() if r in ['proof', 'counter-example'])
        }
        
        f.write(f"{'Solver':<40} {'Total':>8} {'Safe':>8} {'Unsafe':>8} {'Unknown':>8} {'Solved':>8} {'Solve%':>8}\n")
        f.write("-"*100 + "\n")
        
        solve_pct1 = (total_stats1['solved'] / total_stats1['total'] * 100) if total_stats1['total'] > 0 else 0
        f.write(f"{solver1_name:<40} {total_stats1['total']:>8} {total_stats1['safe']:>8} {total_stats1['unsafe']:>8} "
               f"{total_stats1['unknown']:>8} {total_stats1['solved']:>8} {solve_pct1:>7.1f}%\n")
        
        solve_pct2 = (total_stats2['solved'] / total_stats2['total'] * 100) if total_stats2['total'] > 0 else 0
        f.write(f"{solver2_name:<40} {total_stats2['total']:>8} {total_stats2['safe']:>8} {total_stats2['unsafe']:>8} "
               f"{total_stats2['unknown']:>8} {total_stats2['solved']:>8} {solve_pct2:>7.1f}%\n")
        
        f.write("-"*100 + "\n")
        
        safe_diff = total_stats2['safe'] - total_stats1['safe']
        unsafe_diff = total_stats2['unsafe'] - total_stats1['unsafe']
        unknown_diff = total_stats2['unknown'] - total_stats1['unknown']
        solved_diff = total_stats2['solved'] - total_stats1['solved']
        pct_diff = solve_pct2 - solve_pct1
        
        diff_line = f"{'Difference (Solver 2 - Solver 1)':<40} {0:>8} "
        diff_line += f"{safe_diff:>+8} {unsafe_diff:>+8} {unknown_diff:>+8} {solved_diff:>+8} {pct_diff:>+7.1f}%\n"
        f.write(diff_line)
        
        f.write("\n")
        f.write("="*100 + "\n")
    
    print(f"✓ Family comparison tables saved to: {output_file}")


def main():
    """
    Generate statistics for configured solvers.
    """
    # Parse command line arguments
    if len(sys.argv) < 3:
        print("Usage: python generate_solver_statistics.py <log_dir1> <log_dir2> [parser_type]")
        print("  parser_type: 'ric3' or 'ic3ref' (default: 'ric3')")
        print("\nExample:")
        print("  python generate_solver_statistics.py hpc_ric3_dyn_2025 hpc_ric3_mab_2025")
        print("  python generate_solver_statistics.py hpc_IC3REF_solver1 hpc_IC3REF_solver2 ic3ref")
        sys.exit(1)
    
    log_dir1 = sys.argv[1]
    log_dir2 = sys.argv[2]
    parser_type = sys.argv[3] if len(sys.argv) > 3 else 'ric3'
    
    # Validate directories
    if not os.path.exists(log_dir1):
        print(f"Error: Directory not found: {log_dir1}")
        sys.exit(1)
    if not os.path.exists(log_dir2):
        print(f"Error: Directory not found: {log_dir2}")
        sys.exit(1)
    
    # Select parser
    if parser_type.lower() == 'ic3ref':
        parser = parse_ic3ref_log
    else:
        parser = parse_ric3_log
    
    # Parse AIG file list
    aig_list_file = "aig_files_list.txt"
    print(f"Parsing {aig_list_file}...")
    dataset_to_basenames, basename_to_paths = parse_aig_list(aig_list_file)
    aig_dict = dataset_to_basenames
    
    # Configure solvers to analyze
    solvers = [
        (log_dir1, parser),
        (log_dir2, parser),
    ]
    
    # Collect statistics for each solver
    stats_dict = {}
    all_results_dict = {}
    solver_names = []
    
    for solver_name, parser_func in solvers:
        stats, all_results = collect_solver_statistics(aig_dict, solver_name, parser_func)
        stats_dict[solver_name] = stats
        all_results_dict[solver_name] = all_results
        solver_names.append(solver_name)
    
    # Print formatted table
    print_statistics_table(stats_dict, solver_names, all_results_dict)
    
    # Generate CSV file
    csv_filename = "solver_statistics.csv"
    generate_csv_table(stats_dict, solver_names, all_results_dict, csv_filename)
    
    # Generate family comparison tables
    comparison_dir = f"comparison_{log_dir1}_vs_{log_dir2}"
    generate_family_comparison_tables(stats_dict, solver_names, all_results_dict, comparison_dir)


if __name__ == "__main__":
    main()
