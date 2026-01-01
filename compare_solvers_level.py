#!/usr/bin/env python3
"""
Script to compare solver level count for specific families.
Generates scatter plot showing induction depth comparison.

Usage:
    python compare_solvers_level.py <log_dir1> <log_dir2> <families> [parser_type]
    
    log_dir1: First solver log directory
    log_dir2: Second solver log directory
    families: Comma-separated family names (e.g., "hwmcc20,hwmcc24,hwmcc2025")
    parser_type: 'ric3' or 'ic3ref' (default: 'ric3')
    
Example:
    python compare_solvers_level.py hpc_ric3_dyn_20251221_redo hpc_ric3_ic3_mab_20251221_redo "hwmcc20,hwmcc24,hwmcc2025"
"""

import os
import sys
import matplotlib.pyplot as plt
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
                    results[basename] = (time, length, result_type, level)
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


def generate_level_scatter_plot(levels1, levels2, times1, times2, result_types, solver1_short, solver2_short, output_file):
    """Generate level count scatter plot."""
    
    # Set style
    plt.rcParams['font.size'] = 14
    plt.rcParams['axes.labelsize'] = 16
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['xtick.labelsize'] = 14
    plt.rcParams['ytick.labelsize'] = 14
    plt.rcParams['legend.fontsize'] = 14
    plt.rcParams['figure.dpi'] = 300
    
    fig, (ax_main, ax_hist) = plt.subplots(2, 1, figsize=(10, 10), 
                                             gridspec_kw={'height_ratios': [8, 1]})
    
    # Separate by result type
    safe_mask = np.array([r in ['proof', 'safe'] for r in result_types])
    unsafe_mask = np.array([r in ['counter-example', 'unsafe'] for r in result_types])
    
    # Main scatter plot
    # Plot points where solver1 is better (lower solving time)
    better_mask = safe_mask & (times1 < times2)
    if np.any(better_mask):
        ax_main.scatter(levels2[better_mask], levels1[better_mask], 
                       c='blue', marker='+', s=50, linewidths=2, 
                       label='Better performance', alpha=0.7, zorder=3)
    
    # Plot points where solver1 is worse (higher solving time)
    worse_mask = safe_mask & (times1 > times2)
    if np.any(worse_mask):
        ax_main.scatter(levels2[worse_mask], levels1[worse_mask], 
                       c='#FFC0CB', marker='x', s=50, linewidths=2, 
                       label='Worse performance', alpha=0.5, zorder=2)
    
    # Plot points where solving times are equal
    equal_mask = safe_mask & (times1 == times2)
    if np.any(equal_mask):
        ax_main.scatter(levels2[equal_mask], levels1[equal_mask], 
                       c='gray', marker='o', s=30, 
                       label='Equal performance', alpha=0.3, zorder=1)
    
    # Add diagonal line (y=x)
    max_level = max(np.max(levels1), np.max(levels2))
    ax_main.plot([1, max_level], [1, max_level], 'k--', linewidth=1.5, zorder=1)
    
    # Set logarithmic scale
    ax_main.set_xscale('log')
    ax_main.set_yscale('log')
    
    # Set axis limits
    ax_main.set_xlim(0.7, max_level * 1.2)
    ax_main.set_ylim(0.7, max_level * 1.2)
    
    # Labels
    ax_main.set_xlabel(f'{solver2_short} Level Count', fontsize=16, fontweight='bold')
    ax_main.set_ylabel(f'{solver1_short} Level Count', fontsize=16, fontweight='bold')
    
    # Grid
    ax_main.grid(True, which='major', linestyle='--', alpha=0.3, linewidth=0.8, color='gray')
    ax_main.grid(True, which='minor', linestyle=':', alpha=0.15, linewidth=0.5, color='gray')
    
    # Legend
    ax_main.legend(loc='upper left', framealpha=0.95, edgecolor='black')
    
    # Bottom histogram: level count ratio
    # Calculate ratio (solver1 / solver2) for cases where both solved
    valid_mask = (levels1 > 0) & (levels2 > 0) & safe_mask
    ratios = levels1[valid_mask] / levels2[valid_mask]
    
    better_ratios = ratios[ratios <= 1.0]
    worse_ratios = ratios[ratios > 1.0]
    
    # Plot histogram as scatter points
    if len(better_ratios) > 0:
        ax_hist.scatter(better_ratios, np.zeros_like(better_ratios) - 0.5, 
                       c='blue', marker='o', s=20, alpha=0.7, label='Better')
    
    if len(worse_ratios) > 0:
        ax_hist.scatter(worse_ratios, np.zeros_like(worse_ratios) + 0.5, 
                       c='#FFC0CB', marker='o', s=20, alpha=0.5, label='Worse')
    
    # Add box plot
    bp = ax_hist.boxplot([better_ratios, worse_ratios], 
                          positions=[-0.5, 0.5], 
                          vert=False, 
                          widths=0.5,
                          patch_artist=True,
                          showfliers=False)
    bp['boxes'][0].set_facecolor('lightblue')
    bp['boxes'][1].set_facecolor('#FFE0E8')
    
    # Change boxplot lines to gray
    for element in ['whiskers', 'caps', 'medians']:
        for line in bp[element]:
            line.set_color('gray')
            line.set_linewidth(1)
    
    ax_hist.set_xscale('log')
    ax_hist.set_xlim(0.01, 1000)
    ax_hist.set_xlabel(f'Level count ratio ({solver1_short} / {solver2_short})', fontsize=14, fontweight='bold')
    ax_hist.set_yticks([-0.5, 0.5])
    ax_hist.set_yticklabels(['Better', 'Worse'])
    ax_hist.axvline(x=1.0, color='black', linestyle='--', linewidth=1)
    ax_hist.grid(True, which='major', axis='x', linestyle='--', alpha=0.3)
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure in both PNG and PDF formats
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    pdf_file = output_file.replace('.png', '.pdf')
    plt.savefig(pdf_file, bbox_inches='tight')
    print(f"✓ Level scatter plot saved to: {output_file}")
    print(f"✓ PDF version saved to: {pdf_file}")
    plt.close()


def compare_solvers_level(results1, results2, family_basenames, solver1_name, solver2_name, output_file):
    """
    Compare two solvers' level counts for specific families and generate scatter plot.
    """
    # Find common benchmarks in the specified families
    common = family_basenames & set(results1.keys()) & set(results2.keys())
    
    if not common:
        print(f"No common benchmarks found in specified families!")
        return
    
    print(f"Found {len(common)} common benchmarks in specified families")
    
    # Collect data for plotting (only cases that were solved)
    levels1 = []
    levels2 = []
    times1 = []
    times2 = []
    result_types = []
    
    for basename in common:
        time1, _, result1, level1 = results1[basename]
        time2, _, result2, level2 = results2[basename]
        
        # Only include cases where both solvers found a result (not timeout)
        # and level is valid (> 0)
        if level1 > 0 and level2 > 0 and result1 != 'unknown' and result2 != 'unknown':
            levels1.append(level1)
            levels2.append(level2)
            times1.append(time1)
            times2.append(time2)
            
            # Use result from either solver (prefer non-unknown)
            if result1 == 'unknown' and result2 != 'unknown':
                result_type = result2
            elif result2 == 'unknown' and result1 != 'unknown':
                result_type = result1
            else:
                result_type = result1
            result_types.append(result_type)
    
    if len(levels1) == 0:
        print("No valid level data found!")
        return
    
    # Convert to numpy arrays
    levels1 = np.array(levels1)
    levels2 = np.array(levels2)
    times1 = np.array(times1)
    times2 = np.array(times2)
    
    # Generate scatter plot
    generate_level_scatter_plot(levels1, levels2, times1, times2, result_types, solver1_name, solver2_name, output_file)
    
    # Print statistics
    print(f"\nStatistics:")
    print(f"  Total cases with valid levels: {len(levels1)}")
    print(f"  Solver1 avg level: {np.mean(levels1):.2f}")
    print(f"  Solver2 avg level: {np.mean(levels2):.2f}")
    print(f"  Solver1 better (lower time): {np.sum(times1 < times2)}")
    print(f"  Solver2 better (lower time): {np.sum(times2 < times1)}")
    print(f"  Equal times: {np.sum(times1 == times2)}")


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    
    solver1_dirs = sys.argv[1].split(',')
    solver2_dirs = sys.argv[2].split(',')
    families_str = sys.argv[3]
    parser_type = sys.argv[4] if len(sys.argv) > 4 else 'ric3'
    
    # Parse families
    families = [f.strip() for f in families_str.split(',')]
    
    # Select parser
    if parser_type.lower() == 'ic3ref':
        parser_func = parse_ic3ref_log
    else:
        parser_func = parse_ric3_log
    
    print(f"Comparing solvers for families: {', '.join(families)}")
    print(f"  Solver 1: {solver1_dirs[0]}")
    print(f"  Solver 2: {solver2_dirs[0]}")
    print()
    
    # Parse logs
    print("Parsing logs...")
    results1 = parse_log_directories(solver1_dirs, parser_func)
    results2 = parse_log_directories(solver2_dirs, parser_func)
    print(f"  {solver1_dirs[0]}: {len(results1)} logs (merged)")
    print(f"  {solver2_dirs[0]}: {len(results2)} logs (merged)")
    print()
    
    # Get family basenames
    print("Loading family information...")
    family_basenames = get_family_basenames(families)
    print(f"  Total benchmarks in families: {len(family_basenames)}")
    print()
    
    # Create output directory
    solver1_name = solver1_dirs[0]
    solver2_name = solver2_dirs[0]
    output_dir = f"comparison_{solver1_name[:20]}_vs_{solver2_name[:20]}_level"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename - simplify family name
    family_name = '+'.join(families)
    # Simplify hwmcc20+hwmcc24+hwmcc2025 to hwmcc202425
    if family_name == 'hwmcc20+hwmcc24+hwmcc2025':
        family_name = 'hwmcc202425'
    output_file = os.path.join(output_dir, f'{family_name}_level_scatter.png')
    
    # Normalize solver names
    def normalize_solver_name(name):
        """Normalize solver directory name to standard display name."""
        # IC3Ref variants
        if 'IC3REF_mab_20251219_alpha_1_redo' in name:
            return 'IC3Ref-MAB'
        elif 'IC3REF_basic_20251219_redo' in name:
            return 'IC3Ref-Standard'
        elif 'IC3REF_ctgdown_20251219_redo' in name:
            return 'IC3Ref-CtgDown'
        # rIC3 variants
        elif 'ic3_mab_20251221_redo' in name:
            return 'rIC3-MAB'
        elif 'ic3_pure_20251221_redo' in name:
            return 'rIC3-Standard'
        elif 'ic3_ctgdown_20251221_redo' in name or 'hpc_ric3_ctg' in name.lower():
            return 'rIC3-CtgDown'
        elif 'dyn_20251221_redo' in name:
            return 'rIC3-DynAMic'
        else:
            return name.replace('hpc_ric3_', 'rIC3-').replace('hpc_IC3REF_', 'IC3Ref-').replace('_', ' ')
    
    solver1_short = normalize_solver_name(solver1_name)
    solver2_short = normalize_solver_name(solver2_name)
    
    # Create filename with solver names
    filename = f'{solver1_short}_vs_{solver2_short}_{family_name}_level_scatter.png'
    output_file = os.path.join(output_dir, filename)
    
    # Compare solvers
    compare_solvers_level(results1, results2, family_basenames, 
                         solver1_short, solver2_short, output_file)


if __name__ == '__main__':
    main()
