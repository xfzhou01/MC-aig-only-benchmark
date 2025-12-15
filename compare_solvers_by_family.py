#!/usr/bin/env python3
"""
Script to compare solver performance for specific families.
Generates scatter plot with logarithmic axes.

Usage:
    python compare_solvers_by_family.py <log_dir1> <log_dir2> <families> [parser_type]
    
    log_dir1: First solver log directory
    log_dir2: Second solver log directory
    families: Comma-separated family names (e.g., "hwmcc20,hwmcc24,hwmcc2025")
    parser_type: 'ric3' or 'ic3ref' (default: 'ric3')
    
Example:
    python compare_solvers_by_family.py hpc_ric3_dyn_2025 hpc_ric3_mab_2025 "hwmcc20,hwmcc24,hwmcc2025"
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
                time, length, result_type = parser_func(log_path)
                # Only add if not already present (first directory takes precedence)
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


def compare_solvers_by_family(results1, results2, family_basenames, solver1_name, solver2_name, output_file):
    """
    Compare two solvers for specific families and generate scatter plot.
    """
    # Find common benchmarks in the specified families
    common = family_basenames & set(results1.keys()) & set(results2.keys())
    
    if not common:
        print(f"No common benchmarks found in specified families!")
        return
    
    print(f"Found {len(common)} common benchmarks in specified families")
    
    # Collect data for plotting
    times1 = []
    times2 = []
    result_types = []
    
    for basename in common:
        time1, _, result1 = results1[basename]
        time2, _, result2 = results2[basename]
        
        # Use result from either solver (prefer non-unknown)
        if result1 == 'unknown' and result2 != 'unknown':
            result_type = result2
        elif result2 == 'unknown' and result1 != 'unknown':
            result_type = result1
        else:
            result_type = result1
        
        times1.append(time1)
        times2.append(time2)
        result_types.append(result_type)
    
    # Convert to numpy arrays
    times1 = np.array(times1)
    times2 = np.array(times2)
    
    # Generate scatter plot
    generate_scatter_plot(times1, times2, result_types, solver1_name, solver2_name, output_file)
    
    # Print statistics
    print(f"\nStatistics:")
    print(f"  Total cases: {len(times1)}")
    print(f"  Solver1 solved (<3600s): {np.sum(times1 < 3600)}")
    print(f"  Solver2 solved (<3600s): {np.sum(times2 < 3600)}")
    print(f"  Difference: {np.sum(times2 < 3600) - np.sum(times1 < 3600):+d}")
    print(f"  Solver2 faster: {np.sum(times2 < times1)}")
    print(f"  Improvement ratio: {np.sum(times2 < times1) / len(times1) * 100:.1f}%")


def generate_linear_scatter(times1, times2, result_types, solver1_short, solver2_short, output_file):
    """Generate scatter plot with linear scale."""
    
    # Set style
    plt.rcParams['font.size'] = 14
    plt.rcParams['axes.labelsize'] = 16
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['xtick.labelsize'] = 14
    plt.rcParams['ytick.labelsize'] = 14
    plt.rcParams['legend.fontsize'] = 14
    plt.rcParams['figure.dpi'] = 300
    
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Separate by result type
    safe_mask = np.array([r in ['proof', 'safe'] for r in result_types])
    unsafe_mask = np.array([r in ['counter-example', 'unsafe'] for r in result_types])
    unknown_mask = np.array([r == 'unknown' for r in result_types])
    
    # Plot points by result type (times2 on y-axis, times1 on x-axis)
    if np.any(safe_mask):
        ax.scatter(times2[safe_mask], times1[safe_mask], 
                  c='blue', marker='+', s=50, linewidths=2, 
                  label='Safe/Proof', alpha=0.7, zorder=3)
    
    if np.any(unsafe_mask):
        ax.scatter(times2[unsafe_mask], times1[unsafe_mask], 
                  c='#8B008B', marker='x', s=50, linewidths=2, 
                  label='Unsafe/CEX', alpha=0.7, zorder=3)
    
    if np.any(unknown_mask):
        ax.scatter(times2[unknown_mask], times1[unknown_mask], 
                  c='gray', marker='o', s=30, 
                  label='Unknown', alpha=0.5, zorder=2)
    
    # Add diagonal line (y=x)
    ax.plot([0, 3650], [0, 3650], 'k-', linewidth=1.5, zorder=1)
    
    # Add shaded region where solver1 (y-axis, MAB) is better (y < x, below diagonal)
    ax.fill_between([0, 3650], [0, 0], [0, 3650], 
                     color='lightgreen', alpha=0.2, zorder=0)
    
    # Set linear scale
    ax.set_xlim(0, 3650)
    ax.set_ylim(0, 3650)
    
    # Set custom ticks to include 3600 with explicit labels
    tick_positions = [0, 600, 1200, 1800, 2400, 3000, 3600]
    tick_labels = ['0', '600', '1200', '1800', '2400', '3000', r'$3.6\times10^3$']
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels)
    ax.set_yticks(tick_positions)
    ax.set_yticklabels(tick_labels)
    
    # Labels (swapped: solver2 on x-axis, solver1 on y-axis)
    ax.set_xlabel(f'{solver2_short} CPU Time (s)', fontsize=16, fontweight='bold')
    ax.set_ylabel(f'{solver1_short} CPU Time (s)', fontsize=16, fontweight='bold')
    
    # Grid
    ax.grid(True, which='major', linestyle='--', alpha=0.5, linewidth=0.8, color='gray')
    ax.grid(True, which='minor', linestyle=':', alpha=0.3, linewidth=0.5, color='gray')
    
    # Legend
    ax.legend(loc='upper left', framealpha=0.95, edgecolor='black')
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure in both PNG and PDF formats
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    pdf_file = output_file.replace('.png', '.pdf')
    plt.savefig(pdf_file, bbox_inches='tight')
    print(f"✓ Linear scatter plot saved to: {output_file}")
    print(f"✓ Linear PDF version saved to: {pdf_file}")
    plt.close()


def generate_log1_scatter(times1, times2, result_types, solver1_short, solver2_short, output_file):
    """Generate scatter plot with logarithmic scale starting from 1."""
    
    # Set style
    plt.rcParams['font.size'] = 14
    plt.rcParams['axes.labelsize'] = 16
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['xtick.labelsize'] = 14
    plt.rcParams['ytick.labelsize'] = 14
    plt.rcParams['legend.fontsize'] = 14
    plt.rcParams['figure.dpi'] = 300
    
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Separate by result type
    safe_mask = np.array([r in ['proof', 'safe'] for r in result_types])
    unsafe_mask = np.array([r in ['counter-example', 'unsafe'] for r in result_types])
    unknown_mask = np.array([r == 'unknown' for r in result_types])
    
    # Plot points by result type (times2 on y-axis, times1 on x-axis)
    if np.any(safe_mask):
        ax.scatter(times2[safe_mask], times1[safe_mask], 
                  c='blue', marker='+', s=50, linewidths=2, 
                  label='Safe/Proof', alpha=0.7, zorder=3)
    
    if np.any(unsafe_mask):
        ax.scatter(times2[unsafe_mask], times1[unsafe_mask], 
                  c='#8B008B', marker='x', s=50, linewidths=2, 
                  label='Unsafe/CEX', alpha=0.7, zorder=3)
    
    if np.any(unknown_mask):
        ax.scatter(times2[unknown_mask], times1[unknown_mask], 
                  c='gray', marker='o', s=30, 
                  label='Unknown', alpha=0.5, zorder=2)
    
    # Add diagonal line (y=x)
    ax.plot([1, 4500], [1, 4500], 'k-', linewidth=1.5, zorder=1)
    
    # Add shaded region where solver1 (y-axis, MAB) is better (y < x, below diagonal)
    # Only for x > 1000s (hard cases)
    ax.fill_between([1000, 4500], [1, 1], [1000, 4500], 
                     color='lightgreen', alpha=0.2, zorder=0)
    
    # Set logarithmic scale
    ax.set_xscale('log')
    ax.set_yscale('log')
    
    # Set axis limits starting from 1
    ax.set_xlim(1, 4500)
    ax.set_ylim(1, 4500)
    
    # Add custom tick for 3600 on logarithmic scale
    from matplotlib.ticker import FixedLocator, FuncFormatter
    # Get default log ticks and add 3600
    xticks = [1, 10, 100, 1000, 3600]
    yticks = [1, 10, 100, 1000, 3600]
    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
    # Custom formatter to show 3600 in scientific notation
    def custom_formatter(x, pos):
        if x == 3600:
            return r'$3.6\times10^3$'
        elif x >= 1000:
            return f'$10^{int(np.log10(x))}$'
        elif x >= 1:
            return f'$10^{int(np.log10(x))}$'
        return f'{x:.0f}'
    ax.xaxis.set_major_formatter(FuncFormatter(custom_formatter))
    ax.yaxis.set_major_formatter(FuncFormatter(custom_formatter))
    
    # Labels (swapped: solver2 on x-axis, solver1 on y-axis)
    ax.set_xlabel(f'{solver2_short} CPU Time (s)', fontsize=16, fontweight='bold')
    ax.set_ylabel(f'{solver1_short} CPU Time (s)', fontsize=16, fontweight='bold')
    
    # Grid
    ax.grid(True, which='major', linestyle='--', alpha=0.5, linewidth=0.8, color='gray')
    ax.grid(True, which='minor', linestyle=':', alpha=0.3, linewidth=0.5, color='gray')
    
    # Legend
    ax.legend(loc='upper left', framealpha=0.95, edgecolor='black')
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure in both PNG and PDF formats
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    pdf_file = output_file.replace('.png', '.pdf')
    plt.savefig(pdf_file, bbox_inches='tight')
    print(f"✓ Log (1-4500) scatter plot saved to: {output_file}")
    print(f"✓ Log (1-4500) PDF version saved to: {pdf_file}")
    plt.close()


def generate_scatter_plot(times1, times2, result_types, solver1_name, solver2_name, output_file):
    """Generate publication-quality scatter plot."""
    
    # Set style
    plt.rcParams['font.size'] = 14
    plt.rcParams['axes.labelsize'] = 16
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['xtick.labelsize'] = 14
    plt.rcParams['ytick.labelsize'] = 14
    plt.rcParams['legend.fontsize'] = 14
    plt.rcParams['figure.dpi'] = 300
    
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Separate by result type
    safe_mask = np.array([r in ['proof', 'safe'] for r in result_types])
    unsafe_mask = np.array([r in ['counter-example', 'unsafe'] for r in result_types])
    unknown_mask = np.array([r == 'unknown' for r in result_types])
    
    # Plot points by result type (swap axes: times2 on y-axis, times1 on x-axis)
    if np.any(safe_mask):
        ax.scatter(times2[safe_mask], times1[safe_mask], 
                  c='blue', marker='+', s=50, linewidths=2, 
                  label='Safe/Proof', alpha=0.7, zorder=3)
    
    if np.any(unsafe_mask):
        ax.scatter(times2[unsafe_mask], times1[unsafe_mask], 
                  c='#8B008B', marker='x', s=50, linewidths=2, 
                  label='Unsafe/CEX', alpha=0.7, zorder=3)
    
    if np.any(unknown_mask):
        ax.scatter(times2[unknown_mask], times1[unknown_mask], 
                  c='gray', marker='o', s=30, 
                  label='Unknown', alpha=0.5, zorder=2)
    
    # Add diagonal line (y=x)
    ax.plot([0.01, 4500], [0.01, 4500], 'k-', linewidth=1.5, zorder=1)
    
    # Add shaded region where solver1 (y-axis, MAB) is better (y < x, below diagonal)
    # Only for x > 1000s (hard cases)
    ax.fill_between([1000, 4500], [0.01, 0.01], [1000, 4500], 
                     color='lightgreen', alpha=0.2, zorder=0)
    
    # Set logarithmic scale
    ax.set_xscale('log')
    ax.set_yscale('log')
    
    # Set axis limits
    ax.set_xlim(0.01, 4500)
    ax.set_ylim(0.01, 4500)
    
    # Apply custom legend labels
    solver1_short = solver1_name.replace('hpc_ric3_sl_', 'rIC3-').replace('hpc_ric3_', 'rIC3-').replace('hpc_IC3REF_', 'IC3REF-').replace('_', ' ')
    solver2_short = solver2_name.replace('hpc_ric3_sl_', 'rIC3-').replace('hpc_ric3_', 'rIC3-').replace('hpc_IC3REF_', 'IC3REF-').replace('_', ' ')
    
    if 'mab 2025' in solver1_short or 'mab 6 add context' in solver1_short:
        solver1_short = 'rIC3-DynAMic-MAB'
    elif 'dyn 2025' in solver1_short or 'sl dynamic' in solver1_short:
        solver1_short = 'rIC3-DynAMic'
    elif 'ic3 pure' in solver1_short:
        solver1_short = 'rIC3-Standard'
    elif 'ctg 2025' in solver1_short or 'ctg' == solver1_short.strip():
        solver1_short = 'rIC3-CtgDown'
    
    if 'mab 2025' in solver2_short or 'mab 6 add context' in solver2_short:
        solver2_short = 'rIC3-DynAMic-MAB'
    elif 'dyn 2025' in solver2_short or 'sl dynamic' in solver2_short:
        solver2_short = 'rIC3-DynAMic'
    elif 'ic3 pure' in solver2_short:
        solver2_short = 'rIC3-Standard'
    elif 'ctg 2025' in solver2_short or 'ctg' == solver2_short.strip():
        solver2_short = 'rIC3-CtgDown'
    
    # Labels (swapped: solver2 on x-axis, solver1 on y-axis)
    ax.set_xlabel(f'{solver2_short} CPU Time (s)', fontsize=16, fontweight='bold')
    ax.set_ylabel(f'{solver1_short} CPU Time (s)', fontsize=16, fontweight='bold')
    
    # Grid
    ax.grid(True, which='major', linestyle='--', alpha=0.5, linewidth=0.8, color='gray')
    ax.grid(True, which='minor', linestyle=':', alpha=0.3, linewidth=0.5, color='gray')
    
    # Legend
    ax.legend(loc='upper left', framealpha=0.95, edgecolor='black')
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure in both PNG and PDF formats
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    pdf_file = output_file.replace('.png', '.pdf')
    plt.savefig(pdf_file, bbox_inches='tight')
    print(f"\n✓ Scatter plot saved to: {output_file}")
    print(f"✓ PDF version saved to: {pdf_file}")
    
    # Generate linear version
    linear_output = output_file.replace('.png', '_linear.png')
    linear_pdf = output_file.replace('.png', '_linear.pdf')
    generate_linear_scatter(times1, times2, result_types, solver1_short, solver2_short, linear_output)
    
    # Generate log version with range 1-4500
    log_1_output = output_file.replace('.png', '_log1.png')
    log_1_pdf = output_file.replace('.png', '_log1.pdf')
    generate_log1_scatter(times1, times2, result_types, solver1_short, solver2_short, log_1_output)
    
    plt.close()


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    
    log_dir1 = sys.argv[1]
    log_dir2 = sys.argv[2]
    families_str = sys.argv[3]
    parser_type = sys.argv[4] if len(sys.argv) > 4 else 'ric3'
    
    # Parse families
    families = [f.strip() for f in families_str.split(',')]
    
    # Define directory mappings for merged experiments
    dir_mappings = {
        'hpc_ric3_dyn_2025': ['hpc_ric3_dyn_2025', 'hpc_ric3_sl_dynamic'],
        'hpc_ric3_sl_dynamic': ['hpc_ric3_sl_dynamic', 'hpc_ric3_dyn_2025'],
        'hpc_ric3_mab_2025': ['hpc_ric3_mab_2025', 'hpc_ric3_sl_mab_6_add_context_and_reward_decay070'],
        'hpc_ric3_sl_mab_6_add_context_and_reward_decay070': ['hpc_ric3_sl_mab_6_add_context_and_reward_decay070', 'hpc_ric3_mab_2025'],
        'hpc_ric3_ctg_2025': ['hpc_ric3_ctg_2025', 'hpc_ric3_ctg'],
        'hpc_ric3_ctg': ['hpc_ric3_ctg', 'hpc_ric3_ctg_2025'],
        'hpc_ric3_ic3_pure': ['hpc_ric3_ic3_pure', 'hpc_ric3_ic3_pure_2025'],
        'hpc_ric3_ic3_pure_2025': ['hpc_ric3_ic3_pure_2025', 'hpc_ric3_ic3_pure'],
        'hpc_IC3REF_mab_context_po_len_and_delta': ['hpc_IC3REF_mab_context_po_len_and_delta', 'hpc_IC3REF_mab_new_2025'],
        'hpc_IC3REF_mab_new_2025': ['hpc_IC3REF_mab_new_2025', 'hpc_IC3REF_mab_context_po_len_and_delta'],
        'hpc_IC3REF_ctgdown': ['hpc_IC3REF_ctgdown', 'hpc_IC3REF_ctg_new_2025'],
        'hpc_IC3REF_ctg_new_2025': ['hpc_IC3REF_ctg_new_2025', 'hpc_IC3REF_ctgdown']
    }
    
    # Get directories to parse (with merging)
    dirs1 = dir_mappings.get(log_dir1, [log_dir1])
    dirs2 = dir_mappings.get(log_dir2, [log_dir2])
    
    # Select parser
    if parser_type.lower() == 'ic3ref':
        parser_func = parse_ic3ref_log
    else:
        parser_func = parse_ric3_log
    
    print(f"Comparing solvers for families: {', '.join(families)}")
    print(f"  Solver 1: {log_dir1}")
    if len(dirs1) > 1:
        print(f"    Merged with: {', '.join(dirs1[1:])}")
    print(f"  Solver 2: {log_dir2}")
    if len(dirs2) > 1:
        print(f"    Merged with: {', '.join(dirs2[1:])}")
    print()
    
    # Parse logs
    print("Parsing logs...")
    results1 = parse_log_directories(dirs1, parser_func)
    results2 = parse_log_directories(dirs2, parser_func)
    print(f"  {log_dir1}: {len(results1)} logs (merged)")
    print(f"  {log_dir2}: {len(results2)} logs (merged)")
    print()
    
    # Get family basenames
    print("Loading family information...")
    family_basenames = get_family_basenames(families)
    print(f"  Total benchmarks in families: {len(family_basenames)}")
    print()
    
    # Create output directory
    output_dir = f"comparison_{log_dir1}_vs_{log_dir2}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate scatter plot
    family_name = '+'.join(families)
    output_file = os.path.join(output_dir, f'{family_name}_scatter.png')
    compare_solvers_by_family(results1, results2, family_basenames, log_dir1, log_dir2, output_file)


if __name__ == '__main__':
    main()
