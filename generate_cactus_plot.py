#!/usr/bin/env python3
"""
Generate cactus plot comparing two solvers' performance.
X-axis: time threshold (starting from min_time)
Y-axis: number of cases solved within that time threshold

Usage:
    python generate_cactus_plot.py <log_dir1> <log_dir2> [parser_type] [min_time]
    
    log_dir1: First solver log directory
    log_dir2: Second solver log directory
    parser_type: 'ric3' or 'ic3ref' (default: 'ric3')
    min_time: Starting time threshold (default: 100)
    
Example:
    python generate_cactus_plot.py hpc_ric3_dyn_2025 hpc_ric3_mab_2025 ric3 100
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from parse_aig_list import parse_aig_list
from parse_ric3_log import parse_ric3_log
from parse_ic3ref_log import parse_ic3ref_log


def parse_log_directory(log_dir, parser_func):
    """
    Parse all log files in a directory.
    
    Returns:
        dict: {basename: (time, length, result_type)}
    """
    results = {}
    
    if not os.path.exists(log_dir):
        print(f"Error: Directory not found: {log_dir}")
        return results
    
    for filename in os.listdir(log_dir):
        if not filename.endswith('_log.txt'):
            continue
        
        basename = filename.replace('_log.txt', '')
        log_path = os.path.join(log_dir, filename)
        
        try:
            time, length, result_type = parser_func(log_path)
            results[basename] = (time, length, result_type)
        except Exception as e:
            continue
    
    return results


def generate_cactus_plot(times1, times2, solver1_name, solver2_name, 
                         min_time=100, max_time=3600, output_file='cactus_plot.png'):
    """
    Generate a cactus plot comparing two solvers.
    X-axis: time threshold (from min_time to max_time)
    Y-axis: number of cases solved within that time
    
    Args:
        times1: List of solving times for solver 1
        times2: List of solving times for solver 2
        solver1_name: Name of solver 1
        solver2_name: Name of solver 2
        min_time: Starting time threshold (e.g., 100s)
        max_time: Maximum time threshold (e.g., 3600s)
        output_file: Path to save the plot
    """
    times1 = np.array(times1)
    times2 = np.array(times2)
    
    # Set font sizes
    plt.rcParams['font.size'] = 14
    plt.rcParams['axes.labelsize'] = 16
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['xtick.labelsize'] = 14
    plt.rcParams['ytick.labelsize'] = 14
    plt.rcParams['legend.fontsize'] = 14
    plt.rcParams['figure.dpi'] = 300
    
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Create time thresholds from min_time to max_time
    time_thresholds = np.arange(min_time, 3599.99, 10)  # Every 10 seconds, up to 3599.99
    
    # Calculate cumulative solved cases at each threshold
    solved_counts1 = []
    solved_counts2 = []
    
    for threshold in time_thresholds:
        solved_counts1.append(np.sum(times1 <= threshold))
        solved_counts2.append(np.sum(times2 <= threshold))
    
    # Simplify solver names
    solver1_short = solver1_name.replace('hpc_ric3_sl_', 'rIC3-').replace('hpc_ric3_', 'rIC3-').replace('_', ' ')
    solver2_short = solver2_name.replace('hpc_ric3_sl_', 'rIC3-').replace('hpc_ric3_', 'rIC3-').replace('_', ' ')
    
    # Plot curves - X and Y axes swapped
    ax.plot(solved_counts1, time_thresholds, 
            color='lightcoral', linewidth=2.5, alpha=0.7, 
            label=solver1_short, marker='o', markersize=3, markevery=max(1, len(time_thresholds)//50))
    
    ax.plot(solved_counts2, time_thresholds, 
            color='darkred', linewidth=2.5, alpha=0.9,
            label=solver2_short, marker='s', markersize=3, markevery=max(1, len(time_thresholds)//50))
    
    # Set logarithmic scale for y-axis (time)
    ax.set_yscale('log')
    
    # Set y-axis limits starting from min_time, extending to 4500
    ax.set_ylim(min_time, 4500)
    
    # Set y-axis ticks manually
    from matplotlib.ticker import FixedLocator, FuncFormatter
    yticks = [100, 200, 500, 1000, 2000, 3600]
    ax.yaxis.set_major_locator(FixedLocator(yticks))
    
    # Custom formatter to show scientific notation
    def log_formatter(x, pos):
        if x == 100:
            return r'$10^2$'
        elif x == 200:
            return r'$2 \times 10^2$'
        elif x == 500:
            return r'$5 \times 10^2$'
        elif x == 1000:
            return r'$10^3$'
        elif x == 2000:
            return r'$2 \times 10^3$'
        elif x == 3600:
            return r'$3.6 \times 10^3$'
        else:
            return ''
    
    ax.yaxis.set_major_formatter(FuncFormatter(log_formatter))
    
    # Labels - swapped
    ax.set_xlabel('Number of Cases Solved', fontsize=16, fontweight='bold')
    ax.set_ylabel('Time Threshold (s)', fontsize=16, fontweight='bold')
    
    # Grid
    ax.grid(True, which='both', linestyle='--', alpha=0.3, linewidth=0.5, color='gray')
    ax.grid(True, which='minor', linestyle=':', alpha=0.15, linewidth=0.3, color='gray')
    
    # Legend
    ax.legend(loc='lower right', framealpha=0.95, edgecolor='black', fontsize=14)
    
    # Add statistics text at max_time
    solved1_final = solved_counts1[-1]
    solved2_final = solved_counts2[-1]
    
    stats_text = f'At {max_time}s:\n'
    stats_text += f'{solver1_short}: {solved1_final} solved\n'
    stats_text += f'{solver2_short}: {solved2_final} solved\n'
    stats_text += f'Difference: {solved2_final - solved1_final:+d}'
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            fontsize=12, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Cactus plot saved to: {output_file}")
    
    # Show statistics
    print(f"\nStatistics (time range: {min_time}s - {max_time}s):")
    print(f"  {solver1_short}: {solved1_final}/{len(times1)} cases")
    print(f"  {solver2_short}: {solved2_final}/{len(times2)} cases")
    print(f"  Difference: {solved2_final - solved1_final:+d}")


def main():
    """Main function to compare two solvers."""
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    log_dir1 = sys.argv[1]
    log_dir2 = sys.argv[2]
    parser_type = sys.argv[3] if len(sys.argv) > 3 else 'ric3'
    min_time = int(sys.argv[4]) if len(sys.argv) > 4 else 100
    max_time = 3600  # Fixed max time
    
    # Select parser
    if parser_type.lower() == 'ic3ref':
        parser_func = parse_ic3ref_log
    else:
        parser_func = parse_ric3_log
    
    print(f"Comparing solvers:")
    print(f"  Solver 1: {log_dir1}")
    print(f"  Solver 2: {log_dir2}")
    print(f"  Time range: {min_time}s - {max_time}s")
    print()
    
    # Parse logs
    print(f"Parsing {log_dir1}...")
    results1 = parse_log_directory(log_dir1, parser_func)
    print(f"  Found {len(results1)} logs")
    
    print(f"\nParsing {log_dir2}...")
    results2 = parse_log_directory(log_dir2, parser_func)
    print(f"  Found {len(results2)} logs")
    
    # Find common benchmarks
    common_benchmarks = set(results1.keys()) & set(results2.keys())
    print(f"\nFound {len(common_benchmarks)} common benchmarks")
    
    if not common_benchmarks:
        print("Error: No common benchmarks found!")
        sys.exit(1)
    
    # Collect times for common benchmarks
    times1 = []
    times2 = []
    
    for basename in common_benchmarks:
        time1, _, result1 = results1[basename]
        time2, _, result2 = results2[basename]
        
        times1.append(time1)
        times2.append(time2)
    
    # Create output directory
    output_dir = f"comparison_{log_dir1}_vs_{log_dir2}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate cactus plot
    output_file = os.path.join(output_dir, f'cactus_plot_from{min_time}s.png')
    generate_cactus_plot(times1, times2, log_dir1, log_dir2, min_time, max_time, output_file)


if __name__ == '__main__':
    main()
