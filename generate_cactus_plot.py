#!/usr/bin/env python3
"""
Generate cactus plot comparing multiple solvers' performance.
X-axis: time threshold
Y-axis: number of cases solved within that time threshold

Usage:
    python generate_cactus_plot.py --solver dir1 [dir2 ...] --solver dir3 [dir4 ...] [--parser parser_type] [--min-time min_time]
    
    Each --solver specifies one solver with one or more directories to merge
    --parser: 'ric3' or 'ic3ref' (default: 'ric3')
    --min-time: Starting time threshold (default: 0)
    
Example:
    python generate_cactus_plot.py --solver hpc_ric3_mab_2025 hpc_ric3_sl_mab_6_add_context_and_reward_decay070 --solver hpc_ric3_dyn_2025 hpc_ric3_sl_dynamic --solver hpc_ric3_ctg_2025 hpc_ric3_ctg --solver hpc_ric3_ic3_pure hpc_ric3_ic3_pure_2025 --parser ric3
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
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


def generate_cactus_plot(solver_times_list, solver_names, 
                         min_time=0, max_time=3600, output_file='cactus_plot.png'):
    """
    Generate a cactus plot comparing multiple solvers.
    X-axis: time threshold (from min_time to max_time)
    Y-axis: number of cases solved within that time
    
    Args:
        solver_times_list: List of time arrays for each solver
        solver_names: List of solver names
        min_time: Starting time threshold (e.g., 0s)
        max_time: Maximum time threshold (e.g., 3600s)
        output_file: Path to save the plot
    """
    # Convert to numpy arrays
    solver_times_list = [np.array(times) for times in solver_times_list]
    num_solvers = len(solver_times_list)
    
    # Set font sizes
    plt.rcParams['font.size'] = 14
    plt.rcParams['axes.labelsize'] = 16
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['xtick.labelsize'] = 14
    plt.rcParams['ytick.labelsize'] = 14
    plt.rcParams['legend.fontsize'] = 14
    plt.rcParams['figure.dpi'] = 300
    
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Create time thresholds from 0 to max_time
    time_thresholds = np.arange(0, max_time + 0.01, 10)  # Every 10 seconds, from 0 to max_time
    
    # Define colors, markers and styles for multiple solvers
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e']
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p']
    
    # Calculate and plot for each solver
    for idx, (times, solver_name) in enumerate(zip(solver_times_list, solver_names)):
        solved_counts = []
        for threshold in time_thresholds:
            solved_counts.append(np.sum(times <= threshold))
        
        # Simplify solver name
        solver_short = solver_name.replace('hpc_ric3_sl_', 'rIC3-').replace('hpc_ric3_', 'rIC3-').replace('hpc_IC3REF_', 'IC3REF-').replace('_', ' ')
        
        # Plot curve
        color = colors[idx % len(colors)]
        marker = markers[idx % len(markers)]
        ax.plot(time_thresholds, solved_counts, 
                color=color, linewidth=2.5, alpha=0.85,
                label=solver_short, marker=marker, markersize=3, 
                markevery=max(1, len(time_thresholds)//50))
    
    # Set linear scale for x-axis (time)
    ax.set_xlim(0, max_time)
    
    # Set y-axis to start from 300
    ax.set_ylim(300, None)
    
    # Labels
    ax.set_xlabel('Time Threshold (s)', fontsize=16, fontweight='bold')
    ax.set_ylabel('Number of Cases Solved', fontsize=16, fontweight='bold')
    
    # Grid
    ax.grid(True, which='both', linestyle='--', alpha=0.3, linewidth=0.5, color='gray')
    ax.grid(True, which='minor', linestyle=':', alpha=0.15, linewidth=0.3, color='gray')
    
    # Legend
    ax.legend(loc='lower right', framealpha=0.95, edgecolor='black', fontsize=12)
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Cactus plot saved to: {output_file}")
    
    # Show statistics
    print(f"\nStatistics at {max_time}s:")
    for idx, (times, solver_name) in enumerate(zip(solver_times_list, solver_names)):
        solver_short = solver_name.replace('hpc_ric3_sl_', 'rIC3-').replace('hpc_ric3_', 'rIC3-').replace('hpc_IC3REF_', 'IC3REF-').replace('_', ' ')
        solved_final = np.sum(times <= max_time)
        print(f"  {solver_short}: {solved_final}/{len(times)} cases ({solved_final/len(times)*100:.1f}%)")


def main():
    """Main function to compare multiple solvers."""
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    # Parse arguments
    args = sys.argv[1:]
    solver_dirs_list = []  # List of lists, each inner list contains dirs for one solver
    current_solver_dirs = None
    parser_type = 'ric3'
    min_time = 0
    
    i = 0
    while i < len(args):
        if args[i] == '--solver':
            # Save previous solver if exists
            if current_solver_dirs is not None and len(current_solver_dirs) > 0:
                solver_dirs_list.append(current_solver_dirs)
            # Start new solver
            current_solver_dirs = []
            i += 1
        elif args[i] == '--parser':
            # Save current solver before processing parser
            if current_solver_dirs is not None and len(current_solver_dirs) > 0:
                solver_dirs_list.append(current_solver_dirs)
                current_solver_dirs = None
            parser_type = args[i+1]
            i += 2
        elif args[i] == '--min-time':
            # Save current solver before processing min-time
            if current_solver_dirs is not None and len(current_solver_dirs) > 0:
                solver_dirs_list.append(current_solver_dirs)
                current_solver_dirs = None
            min_time = int(args[i+1])
            i += 2
        else:
            # This is a directory for current solver
            if current_solver_dirs is not None:
                current_solver_dirs.append(args[i])
            i += 1
    
    # Don't forget the last solver
    if current_solver_dirs is not None and len(current_solver_dirs) > 0:
        solver_dirs_list.append(current_solver_dirs)
    
    if len(solver_dirs_list) < 2:
        print("Error: At least 2 solvers are required (use --solver for each)")
        print(__doc__)
        sys.exit(1)
    
    max_time = 3599  # Fixed max time
    
    # Select parser
    if parser_type.lower() == 'ic3ref':
        parser_func = parse_ic3ref_log
    else:
        parser_func = parse_ric3_log
    
    print(f"Comparing {len(solver_dirs_list)} solvers:")
    for i, dirs in enumerate(solver_dirs_list, 1):
        print(f"  Solver {i}: {' + '.join(dirs)}")
    print(f"  Parser: {parser_type}")
    print(f"  Time range: {min_time}s - {max_time}s")
    print()
    
    # Parse logs for all solvers
    all_results = []
    solver_names = []
    for dirs in solver_dirs_list:
        print(f"Parsing {' + '.join(dirs)}...")
        results = parse_log_directories(dirs, parser_func)
        print(f"  Found {len(results)} logs (merged)")
        all_results.append(results)
        # Use first directory name as solver name
        solver_names.append(dirs[0])
    
    # Find common benchmarks across all solvers
    common_benchmarks = set(all_results[0].keys())
    for results in all_results[1:]:
        common_benchmarks &= set(results.keys())
    
    print(f"\nFound {len(common_benchmarks)} common benchmarks")
    
    if not common_benchmarks:
        print("Error: No common benchmarks found!")
        sys.exit(1)
    
    # Collect times for common benchmarks from all solvers
    solver_times_list = []
    for results in all_results:
        times = []
        for basename in common_benchmarks:
            time, _, _ = results[basename]
            times.append(time)
        solver_times_list.append(times)
    
    # Create output directory
    # Create output directory
    output_dir = f"comparison_{'_vs_'.join([d[0][:15] for d in solver_dirs_list])}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate cactus plot
    output_file = os.path.join(output_dir, f'cactus_plot_from{min_time}s.png')
    generate_cactus_plot(solver_times_list, solver_names, min_time, max_time, output_file)

if __name__ == '__main__':
    main()
if __name__ == '__main__':
    main()
