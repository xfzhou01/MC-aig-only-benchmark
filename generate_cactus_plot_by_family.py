#!/usr/bin/env python3
"""
Generate cactus plot for specific families comparing multiple solvers.
X-axis: Time threshold
Y-axis: Number of cases solved

Usage:
    python generate_cactus_plot_by_family.py --solver dir1 [dir2 ...] --solver dir3 [dir4 ...] --families family1,family2,... [--parser parser_type] [--min-time min_time] [--ic3ref] [--merge-both]
    
Example:
    python generate_cactus_plot_by_family.py --solver hpc_ric3_mab_2025 hpc_ric3_sl_mab_6_add_context_and_reward_decay070 --solver hpc_ric3_dyn_2025 hpc_ric3_sl_dynamic --families hwmcc20,hwmcc24,hwmcc2025 --parser ric3
    python generate_cactus_plot_by_family.py --solver hpc_IC3REF_basic_new hpc_IC3REF_basic_new_2025 --solver hpc_IC3REF_mab_context_po_len_and_delta hpc_IC3REF_mab_new_2025 --families hwmcc20,hwmcc24,hwmcc2025 --ic3ref
    python generate_cactus_plot_by_family.py --families hwmcc20,hwmcc24,hwmcc2025 --merge-both
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter
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


def generate_cactus_plot(solver_times_list, solver_names, 
                         min_time=0, max_time=3600, output_file='cactus_plot.png', use_ic3ref=False):
    """Generate cactus plot for multiple solvers."""
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
        
        # Normalize solver name to standard display name
        def normalize_solver_name(name, is_ic3ref_mode):
            """Normalize solver directory name to standard display name."""
            # First check for _redo patterns
            if 'ic3_mab_20251221_redo' in name:
                return 'rIC3-DynAMic-MAB'
            elif 'ic3_pure_20251221_redo' in name:
                return 'rIC3-Standard'
            elif 'ic3_ctgdown_20251221_redo' in name:
                return 'rIC3-CtgDown'
            elif 'dyn_20251221_redo' in name:
                return 'rIC3-DynAMic'
            elif 'IC3REF_mab_20251219_alpha_1_redo' in name:
                return 'IC3Ref-MAB'
            elif 'IC3REF_basic_20251219_redo' in name:
                return 'IC3Ref-Standard'
            elif 'IC3REF_ctgdown_20251219_redo' in name:
                return 'IC3Ref-CtgDown'
            
            # Fallback to old pattern matching
            solver_short = name.replace('hpc_ric3_sl_', 'rIC3-').replace('hpc_ric3_', 'rIC3-').replace('hpc_IC3REF_', 'IC3Ref-').replace('_', ' ')
            
            if is_ic3ref_mode:
                if 'basic new' in solver_short or 'basic' in solver_short:
                    return 'IC3Ref-Standard'
                elif 'ctg' in solver_short and 'mab' not in solver_short:
                    return 'IC3Ref-CtgDown'
                elif 'mab' in solver_short:
                    return 'IC3Ref-MAB'
            else:
                if 'mab 2025' in solver_short or 'mab 6 add context' in solver_short:
                    return 'rIC3-DynAMic-MAB'
                elif 'dyn 2025' in solver_short or 'sl dynamic' in solver_short:
                    return 'rIC3-DynAMic'
                elif 'ic3 pure' in solver_short or 'pure' in solver_short:
                    return 'rIC3-Standard'
                elif 'ctg 2025' in solver_short or 'ctg' in solver_short:
                    return 'rIC3-CtgDown'
            
            return solver_short
        
        is_ic3ref_context = (use_ic3ref == True or (use_ic3ref == 'mixed' and 'IC3REF' in solver_name))
        solver_short = normalize_solver_name(solver_name, is_ic3ref_context)
        
        # Plot curve
        color = colors[idx % len(colors)]
        marker = markers[idx % len(markers)]
        ax.plot(time_thresholds, solved_counts, 
                color=color, linewidth=2.5, alpha=0.85,
                label=solver_short, marker=marker, markersize=3, 
                markevery=max(1, len(time_thresholds)//50))
    
    # Set linear scale for x-axis (time) - extend to 3650 to show 3600 tick
    ax.set_xlim(0, 3650)
    
    # Set x-axis ticks every 600 seconds (0, 600, 1200, 1800, 2400, 3000, 3600)
    ax.set_xticks(np.arange(0, 3601, 600))
    
    # Set y-axis start based on solver type
    if use_ic3ref == True or use_ic3ref == 'mixed':
        ax.set_ylim(300, 470)  # IC3REF or mixed mode: from 300 to 470
    else:
        ax.set_ylim(400, None)  # rIC3 only: start from 400
    
    # Labels
    ax.set_xlabel('Time Threshold (s)', fontsize=16, fontweight='bold')
    ax.set_ylabel('Number of Cases Solved', fontsize=16, fontweight='bold')
    
    # Grid
    ax.grid(True, which='both', linestyle='--', alpha=0.3, linewidth=0.5, color='gray')
    ax.grid(True, which='minor', linestyle=':', alpha=0.15, linewidth=0.3, color='gray')
    
    # Legend
    ax.legend(loc='lower right', framealpha=0.95, edgecolor='black', fontsize=14)
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure in both PNG and PDF formats
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    pdf_file = output_file.replace('.png', '.pdf')
    plt.savefig(pdf_file, bbox_inches='tight')
    print(f"\n✓ Cactus plot saved to: {output_file}")
    print(f"✓ PDF version saved to: {pdf_file}")
    
    # Show statistics
    print(f"\nStatistics at {int(max_time)}s:")
    for idx, (times, solver_name) in enumerate(zip(solver_times_list, solver_names)):
        is_ic3ref_context = (use_ic3ref == True or (use_ic3ref == 'mixed' and 'IC3REF' in solver_name))
        solver_short = normalize_solver_name(solver_name, is_ic3ref_context)
        solved_final = np.sum(times <= max_time)
        print(f"  {solver_short}: {solved_final}/{len(times)} cases ({solved_final/len(times)*100:.1f}%)")


def main():
    # Parse arguments
    args = sys.argv[1:]
    solver_dirs_list = []  # List of lists, each inner list contains dirs for one solver
    current_solver_dirs = None
    families_str = None
    parser_type = 'ric3'
    min_time = 0
    use_ic3ref = False
    merge_both = False
    
    i = 0
    while i < len(args):
        if args[i] == '--solver':
            # Save previous solver if exists
            if current_solver_dirs is not None and len(current_solver_dirs) > 0:
                solver_dirs_list.append(current_solver_dirs)
            # Start new solver
            current_solver_dirs = []
            i += 1
        elif args[i] == '--families':
            # Save current solver before processing families
            if current_solver_dirs is not None and len(current_solver_dirs) > 0:
                solver_dirs_list.append(current_solver_dirs)
                current_solver_dirs = None
            families_str = args[i+1]
            i += 2
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
        elif args[i] == '--ic3ref':
            # Save current solver before processing ic3ref flag
            if current_solver_dirs is not None and len(current_solver_dirs) > 0:
                solver_dirs_list.append(current_solver_dirs)
                current_solver_dirs = None
            use_ic3ref = True
            parser_type = 'ic3ref'
            i += 1
        elif args[i] == '--merge-both':
            # Save current solver before processing merge-both flag
            if current_solver_dirs is not None and len(current_solver_dirs) > 0:
                solver_dirs_list.append(current_solver_dirs)
                current_solver_dirs = None
            merge_both = True
            i += 1
        else:
            # This is a directory for current solver
            if current_solver_dirs is not None:
                current_solver_dirs.append(args[i])
            i += 1
    
    # Don't forget the last solver
    if current_solver_dirs is not None and len(current_solver_dirs) > 0:
        solver_dirs_list.append(current_solver_dirs)
    
    if not families_str:
        print("Error: --families parameter is required")
        print(__doc__)
        sys.exit(1)
    
    # Handle merge-both mode
    if merge_both:
        # Use predefined solver configurations for both rIC3 and IC3REF
        solver_dirs_list = [
            # rIC3 solvers
            ['hpc_ric3_ic3_pure_20251221_redo'],
            ['hpc_ric3_ic3_ctgdown_20251221_redo'],
            ['hpc_ric3_dyn_20251221_redo'],
            ['hpc_ric3_ic3_mab_20251221_redo'],
            # IC3REF solvers
            ['hpc_IC3REF_basic_20251219_redo'],
            ['hpc_IC3REF_ctgdown_20251219_redo'],
            ['hpc_IC3REF_mab_20251219_alpha_1_redo']
        ]
        use_ic3ref = 'mixed'  # Special mode for mixed solvers
    elif len(solver_dirs_list) < 2:
        print("Error: At least 2 solvers are required (use --solver for each)")
        print(__doc__)
        sys.exit(1)
    
    max_time = 3599
    
    # Parse families
    families = [f.strip() for f in families_str.split(',')]
    
    print(f"Generating cactus plot for {len(solver_dirs_list)} solvers")
    print(f"Families: {', '.join(families)}")
    
    # Parse logs for all solvers
    print("\nParsing logs...")
    all_results = []
    solver_names = []
    
    if merge_both:
        # Mixed mode: use appropriate parser for each solver
        for i, dirs in enumerate(solver_dirs_list):
            if 'IC3REF' in dirs[0]:
                parser_func = parse_ic3ref_log
                print(f"  {' + '.join(dirs)}: ", end='')
            else:
                parser_func = parse_ric3_log
                print(f"  {' + '.join(dirs)}: ", end='')
            results = parse_log_directories(dirs, parser_func)
            all_results.append(results)
            solver_names.append(dirs[0])
            print(f"{len(results)} logs (merged)")
    else:
        # Single mode: use one parser for all
        if parser_type.lower() == 'ic3ref':
            parser_func = parse_ic3ref_log
            use_ic3ref = True  # Set use_ic3ref when parser is ic3ref
        else:
            parser_func = parse_ric3_log
        
        for i, dirs in enumerate(solver_dirs_list, 1):
            print(f"  Solver {i}: {' + '.join(dirs)}")
        print(f"  Parser: {parser_type}")
        print(f"  Time range: {min_time}s - {max_time}s")
        print()
        
        print("Parsing logs...")
        for dirs in solver_dirs_list:
            results = parse_log_directories(dirs, parser_func)
            all_results.append(results)
            solver_names.append(dirs[0])
            print(f"  {' + '.join(dirs)}: {len(results)} logs (merged)")
    
    # Get family basenames
    print("\nLoading family information...")
    family_basenames = get_family_basenames(families)
    print(f"  Total benchmarks in families: {len(family_basenames)}")
    
    # Find common benchmarks across all solvers and families
    common_benchmarks = family_basenames & set(all_results[0].keys())
    for results in all_results[1:]:
        common_benchmarks &= set(results.keys())
    
    print(f"\nFound {len(common_benchmarks)} common benchmarks")
    
    if not common_benchmarks:
        print("Error: No common benchmarks found!")
        sys.exit(1)
    
    # Collect times for all solvers
    solver_times_list = []
    for results in all_results:
        times = []
        for basename in common_benchmarks:
            time, _, _ = results[basename]
            times.append(time)
        solver_times_list.append(times)
    
    # Create output directory
    output_dir = f"comparison_{'_vs_'.join([d[0][:15] for d in solver_dirs_list])}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate cactus plot
    family_name = '+'.join(families)
    output_file = os.path.join(output_dir, f'{family_name}_cactus_from{min_time}s.png')
    generate_cactus_plot(solver_times_list, solver_names, min_time, max_time, output_file, use_ic3ref)


if __name__ == '__main__':
    main()
