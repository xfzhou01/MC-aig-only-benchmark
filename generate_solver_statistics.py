#!/usr/bin/env python3
"""
Generate statistics table for solver performance across different families.
Shows how many safe/unsafe/unknown cases each solver solved in each family.
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
        dict: {family: {'safe': count, 'unsafe': count, 'unknown': count, 'total': count}}
    """
    # Parse all logs once
    print(f"Parsing logs in {log_dir}...")
    results = {}
    
    if not os.path.exists(log_dir):
        print(f"Error: Directory not found: {log_dir}")
        return {}
    
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
        total_count = len(benchmarks)
        
        for aig_file in benchmarks:
            basename = os.path.splitext(aig_file)[0]
            
            if basename in results:
                result_type = results[basename]
                if result_type == 'proof':
                    safe_count += 1
                elif result_type == 'counter-example':
                    unsafe_count += 1
                elif result_type == 'unknown':
                    unknown_count += 1
        
        stats[family] = {
            'safe': safe_count,
            'unsafe': unsafe_count,
            'unknown': unknown_count,
            'total': total_count,
            'solved': safe_count + unsafe_count
        }
    
    return stats


def print_statistics_table(stats_dict, solver_names):
    """
    Print statistics table in a formatted way.
    
    Args:
        stats_dict: {solver_name: {family: {'safe': ..., 'unsafe': ..., ...}}}
        solver_names: List of solver names in order
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
        total_solve_pct = (total_solved / total_benchmarks * 100) if total_benchmarks > 0 else 0
        print(f"{'TOTAL':<20} {total_benchmarks:>8} {total_safe:>8} {total_unsafe:>8} {total_unknown:>8} {total_solved:>8} {total_solve_pct:>7.1f}%")
        print("-"*120)


def generate_csv_table(stats_dict, solver_names, output_file):
    """
    Generate CSV file with statistics.
    
    Args:
        stats_dict: {solver_name: {family: {'safe': ..., 'unsafe': ..., ...}}}
        solver_names: List of solver names
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
            
            # Write total row
            total_safe = sum(s['safe'] for s in stats.values())
            total_unsafe = sum(s['unsafe'] for s in stats.values())
            total_unknown = sum(s['unknown'] for s in stats.values())
            total_benchmarks = sum(s['total'] for s in stats.values())
            total_solved = sum(s['solved'] for s in stats.values())
            total_solve_pct = (total_solved / total_benchmarks * 100) if total_benchmarks > 0 else 0
            
            f.write(f"{solver_name},TOTAL,{total_benchmarks},{total_safe},{total_unsafe},{total_unknown},{total_solved},{total_solve_pct:.1f}\n")
    
    print(f"\n✓ CSV table saved to: {output_file}")


def generate_family_comparison_tables(stats_dict, solver_names, output_dir):
    """
    Generate comparison tables for each family and save to text file.
    
    Args:
        stats_dict: {solver_name: {family: {'safe': ..., 'unsafe': ..., ...}}}
        solver_names: List of solver names (should be 2 for comparison)
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
        
        # Overall summary
        f.write("="*100 + "\n")
        f.write("Overall Summary\n")
        f.write("="*100 + "\n\n")
        
        total_stats1 = {
            'total': sum(s['total'] for s in stats_dict[solver_names[0]].values()),
            'safe': sum(s['safe'] for s in stats_dict[solver_names[0]].values()),
            'unsafe': sum(s['unsafe'] for s in stats_dict[solver_names[0]].values()),
            'unknown': sum(s['unknown'] for s in stats_dict[solver_names[0]].values()),
            'solved': sum(s['solved'] for s in stats_dict[solver_names[0]].values())
        }
        
        total_stats2 = {
            'total': sum(s['total'] for s in stats_dict[solver_names[1]].values()),
            'safe': sum(s['safe'] for s in stats_dict[solver_names[1]].values()),
            'unsafe': sum(s['unsafe'] for s in stats_dict[solver_names[1]].values()),
            'unknown': sum(s['unknown'] for s in stats_dict[solver_names[1]].values()),
            'solved': sum(s['solved'] for s in stats_dict[solver_names[1]].values())
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
    # Parse AIG file list
    aig_list_file = "aig_files_list.txt"
    print(f"Parsing {aig_list_file}...")
    dataset_to_basenames, basename_to_paths = parse_aig_list(aig_list_file)
    aig_dict = dataset_to_basenames
    
    # Configure solvers to analyze
    solvers = [
        ("hpc_ric3_sl_dynamic", parse_ric3_log),
        ("hpc_ric3_sl_mab_6_add_context_and_reward_decay070", parse_ric3_log),
    ]
    
    # You can also add IC3REF solvers:
    # solvers.append(("hpc_IC3REF_mab_alpha_1p0", parse_ic3ref_log))
    
    print(f"\n{'='*120}")
    print(f"Analyzing {len(solvers)} solver(s):")
    for solver_name, _ in solvers:
        print(f"  - {solver_name}")
    print(f"{'='*120}\n")
    
    # Collect statistics for each solver
    stats_dict = {}
    solver_names = []
    
    for solver_name, parser_func in solvers:
        stats = collect_solver_statistics(aig_dict, solver_name, parser_func)
        stats_dict[solver_name] = stats
        solver_names.append(solver_name)
    
    # Print formatted table
    print_statistics_table(stats_dict, solver_names)
    
    # Generate CSV file
    csv_filename = "solver_statistics.csv"
    generate_csv_table(stats_dict, solver_names, csv_filename)
    
    # Generate family comparison tables
    solver1_short = solvers[0][0].replace('hpc_ric3_sl_', '').replace('hpc_IC3REF_', '')
    solver2_short = solvers[1][0].replace('hpc_ric3_sl_', '').replace('hpc_IC3REF_', '')
    comparison_dir = f"comparison_{solver1_short}_vs_{solver2_short}"
    generate_family_comparison_tables(stats_dict, solver_names, comparison_dir)


if __name__ == "__main__":
    main()
