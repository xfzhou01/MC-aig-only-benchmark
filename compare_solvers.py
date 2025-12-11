#!/usr/bin/env python3
"""
Script to compare solver performance between two log directories.
Generates scatter plots with logarithmic axes for paper-quality visualization.

Usage:
    python compare_solvers.py <log_dir1> <log_dir2> [parser_type]
    
    log_dir1: First solver log directory
    log_dir2: Second solver log directory
    parser_type: 'ric3' or 'ic3ref' (default: 'ric3')
    
Example:
    python compare_solvers.py hpc_ric3_dyn_2025 hpc_ric3_mab_2025
    python compare_solvers.py hpc_IC3REF_solver1 hpc_IC3REF_solver2 ic3ref
"""

import os
import re
import sys
import matplotlib.pyplot as plt
import numpy as np
from parse_aig_list import parse_aig_list
from parse_ric3_log import parse_ric3_log
from parse_ic3ref_log import parse_ic3ref_log


def get_log_basename(aig_filename):
    """
    Convert AIG filename to corresponding log filename.
    Example: 139442p0.aig -> 139442p0_log.txt
    """
    basename = os.path.splitext(aig_filename)[0]
    return f"{basename}_log.txt"


def parse_log_directory(log_dir, parser_func):
    """
    Parse all log files in a directory using the specified parser.
    
    Args:
        log_dir: Path to log directory
        parser_func: Either parse_ric3_log or parse_ic3ref_log
        
    Returns:
        dict: {basename: (time, length, result_type)}
    """
    results = {}
    
    if not os.path.exists(log_dir):
        print(f"Warning: Directory not found: {log_dir}")
        return results
    
    for filename in os.listdir(log_dir):
        if not filename.endswith('_log.txt'):
            continue
        
        # Extract basename (remove _log.txt suffix)
        basename = filename.replace('_log.txt', '')
        log_path = os.path.join(log_dir, filename)
        
        try:
            time, length, result_type = parser_func(log_path)
            results[basename] = (time, length, result_type)
        except Exception as e:
            print(f"Error parsing {filename}: {e}")
            continue
    
    return results


def compare_solver_performance(aig_dict, log_dir1, log_dir2, parser_func, 
                                family='hwmcc08', output_file='tmp.png'):
    """
    Compare solver performance between two log directories for a specific family.
    
    Args:
        aig_dict: Dictionary from parse_aig_list (dataset -> basenames)
        log_dir1: First log directory path
        log_dir2: Second log directory path
        parser_func: Either parse_ric3_log or parse_ic3ref_log
        family: Dataset family name (default: 'hwmcc08')
        output_file: Output PNG filename (default: 'tmp.png')
    """
    # Get benchmark list for the specified family
    if family not in aig_dict:
        print(f"Error: Family '{family}' not found in AIG list")
        print(f"Available families: {list(aig_dict.keys())}")
        return
    
    benchmarks = aig_dict[family]  # List of basenames like ['139442p0.aig', ...]
    print(f"Found {len(benchmarks)} benchmarks in {family}")
    
    # Parse both log directories
    print(f"\nParsing {log_dir1}...")
    results1 = parse_log_directory(log_dir1, parser_func)
    print(f"  Parsed {len(results1)} logs")
    
    print(f"\nParsing {log_dir2}...")
    results2 = parse_log_directory(log_dir2, parser_func)
    print(f"  Parsed {len(results2)} logs")
    
    # Match benchmarks and collect timing data
    times1 = []
    times2 = []
    labels = []
    result_types = []
    
    for aig_file in benchmarks:
        basename = os.path.splitext(aig_file)[0]
        
        if basename in results1 and basename in results2:
            time1, _, result1 = results1[basename]
            time2, _, result2 = results2[basename]
            
            # Determine result type: if one is unknown, use the other's result
            if result1 == 'unknown' and result2 != 'unknown':
                final_result = result2
            elif result2 == 'unknown' and result1 != 'unknown':
                final_result = result1
            elif result1 != 'unknown':
                # Both have results, they should agree (use result1)
                final_result = result1
            else:
                # Both unknown
                final_result = 'unknown'
            
            times1.append(time1)
            times2.append(time2)
            labels.append(basename)
            result_types.append(final_result)
    
    print(f"\nMatched {len(times1)} common benchmarks")
    
    if len(times1) == 0:
        print("Error: No matching benchmarks found!")
        return
    
    # Generate scatter plot
    plot_scatter(times1, times2, labels, log_dir1, log_dir2, family, output_file, result_types)


def plot_scatter(times1, times2, labels, solver1_name, solver2_name, 
                 family, output_file='tmp.png', result_types=None):
    """
    Create a high-quality scatter plot comparing two solvers.
    
    Args:
        times1: List of times for solver 1
        times2: List of times for solver 2
        labels: List of benchmark names
        solver1_name: Name of first solver (for x-axis label)
        solver2_name: Name of second solver (for y-axis label)
        family: Dataset family name
        output_file: Output filename
        result_types: List of result types ('proof', 'counter-example', 'unknown')
    """
    # Set paper-quality plot style
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.size'] = 14
    plt.rcParams['axes.labelsize'] = 16
    plt.rcParams['xtick.labelsize'] = 14
    plt.rcParams['ytick.labelsize'] = 14
    plt.rcParams['legend.fontsize'] = 14
    plt.rcParams['figure.dpi'] = 300
    
    fig, ax = plt.subplots(figsize=(9, 9))
    
    # Convert to numpy arrays for easier manipulation
    times1 = np.array(times1)
    times2 = np.array(times2)
    
    timeout_val = 3600
    
    # Add shaded region in lower right (Solver 2 faster, i.e., y < x)
    # This region shows where MAB (y-axis) is faster than Dynamic (x-axis)
    # Green area: from x=1000 onwards, between y=0.1 and the diagonal line y=x
    ax.fill_between([1000, 4500], [0.1, 0.1], [1000, 4500], 
                     color='lightgreen', alpha=0.2, zorder=0)
    
    # Plot points by result type
    if result_types is not None:
        result_types = np.array(result_types)
        
        # Safe (proof) - blue +
        safe_mask = (result_types == 'proof')
        if np.any(safe_mask):
            ax.scatter(times1[safe_mask], times2[safe_mask], 
                      c='blue', s=50, alpha=0.6, marker='+', linewidths=2, 
                      label='safe')
        
        # Unsafe (counter-example) - purple/magenta ×
        unsafe_mask = (result_types == 'counter-example')
        if np.any(unsafe_mask):
            ax.scatter(times1[unsafe_mask], times2[unsafe_mask], 
                      c='#8B008B', s=50, alpha=0.6, marker='x', linewidths=2,
                      label='unsafe')
        
        # Unknown - gray
        unknown_mask = (result_types == 'unknown')
        if np.any(unknown_mask):
            ax.scatter(times1[unknown_mask], times2[unknown_mask], 
                      c='gray', s=30, alpha=0.4, marker='o',
                      label='unknown')
    else:
        # Fallback: plot all as blue
        ax.scatter(times1, times2, c='blue', s=50, alpha=0.6, marker='+', linewidths=2)
    
    # Add diagonal line (y=x) - solid black
    min_val = 0.01
    max_val = timeout_val * 1.2
    ax.plot([min_val, max_val], [min_val, max_val], 
            'k-', linewidth=2, alpha=0.8, zorder=5)
    
    # Set logarithmic scale
    ax.set_xscale('log')
    ax.set_yscale('log')
    
    # Set axis limits - extend to 4500
    ax.set_xlim(0.01, 4500)
    ax.set_ylim(0.01, 4500)
    
    # Set custom tick labels to include 3.6×10³
    from matplotlib.ticker import LogLocator, NullFormatter, FuncFormatter
    
    # Define major ticks
    major_ticks = [0.01, 0.1, 1, 10, 100, 1000, 3600]
    ax.set_xticks(major_ticks)
    ax.set_yticks(major_ticks)
    
    # Custom formatter - use scientific notation for all ticks
    def custom_formatter(x, pos):
        if x >= 1000:
            # Scientific notation for large numbers
            exponent = int(np.log10(x))
            mantissa = x / (10 ** exponent)
            if mantissa == 1.0:
                return rf'$10^{exponent}$'
            else:
                return rf'${mantissa:.1f} \times 10^{exponent}$'
        elif x >= 1:
            return rf'$10^{int(np.log10(x))}$'
        else:
            # For small numbers like 0.01, 0.1
            exponent = int(np.floor(np.log10(x)))
            mantissa = x / (10 ** exponent)
            if abs(mantissa - 1.0) < 0.01:
                return rf'$10^{{{exponent}}}$'
            else:
                return rf'${mantissa:.1f} \times 10^{{{exponent}}}$'
    
    ax.xaxis.set_major_formatter(FuncFormatter(custom_formatter))
    ax.yaxis.set_major_formatter(FuncFormatter(custom_formatter))
    
    # Labels - simplified names
    solver1_short = solver1_name.replace('hpc_ric3_sl_', 'rIC3-').replace('_', ' ')
    solver2_short = solver2_name.replace('hpc_ric3_sl_', 'rIC3-').replace('_', ' ')
    
    ax.set_xlabel(f'{solver1_short}: CPU time (s)', fontsize=16)
    ax.set_ylabel(f'{solver2_short}: CPU time (s)', fontsize=16)
    
    # Dense grid
    ax.grid(True, which='both', linestyle='-', alpha=0.3, linewidth=0.5, color='gray')
    ax.grid(True, which='minor', linestyle='-', alpha=0.15, linewidth=0.3, color='gray')
    
    # Legend
    ax.legend(loc='lower right', framealpha=0.95, edgecolor='black', fontsize=14)
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Scatter plot saved to: {output_file}")
    
    # Show statistics
    solved1 = np.sum(times1 < timeout_val)
    solved2 = np.sum(times2 < timeout_val)
    both_solved = np.sum((times1 < timeout_val) & (times2 < timeout_val))
    
    print(f"\n{'='*60}")
    print(f"Statistics:")
    print(f"{'='*60}")
    print(f"Total benchmarks: {len(times1)}")
    print(f"Solver 1 solved: {solved1} ({solved1/len(times1)*100:.1f}%)")
    print(f"Solver 2 solved: {solved2} ({solved2/len(times2)*100:.1f}%)")
    print(f"Both solved: {both_solved} ({both_solved/len(times1)*100:.1f}%)")
    
    plt.close()


def main():
    """
    Generate comparison plots for all families between two solver configurations.
    """
    # Parse command line arguments
    if len(sys.argv) < 3:
        print("Usage: python compare_solvers.py <log_dir1> <log_dir2> [parser_type]")
        print("  parser_type: 'ric3' or 'ic3ref' (default: 'ric3')")
        print("\nExample:")
        print("  python compare_solvers.py hpc_ric3_dyn_2025 hpc_ric3_mab_2025")
        print("  python compare_solvers.py hpc_IC3REF_solver1 hpc_IC3REF_solver2 ic3ref")
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
    aig_dict = dataset_to_basenames  # Use the first dict: dataset -> basenames
    
    # Create output directory
    solver1_short = os.path.basename(log_dir1).replace('hpc_ric3_sl_', '').replace('hpc_IC3REF_', '')
    solver2_short = os.path.basename(log_dir2).replace('hpc_ric3_sl_', '').replace('hpc_IC3REF_', '')
    output_dir = f"comparison_{solver1_short}_vs_{solver2_short}"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"\nCreated output directory: {output_dir}")
    else:
        print(f"\nUsing output directory: {output_dir}")
    
    print(f"\n{'='*60}")
    print(f"Comparing solvers across all families:")
    print(f"  Solver 1: {log_dir1}")
    print(f"  Solver 2: {log_dir2}")
    print(f"{'='*60}\n")
    
    # Generate plots for each family
    families = sorted(aig_dict.keys())
    print(f"Found {len(families)} families: {', '.join(families)}\n")
    
    for i, family in enumerate(families, 1):
        print(f"[{i}/{len(families)}] Processing {family}...")
        output_file = os.path.join(output_dir, f"{family}.png")
        
        try:
            compare_solver_performance(
                aig_dict=aig_dict,
                log_dir1=log_dir1,
                log_dir2=log_dir2,
                parser_func=parser,
                family=family,
                output_file=output_file
            )
        except Exception as e:
            print(f"  Error processing {family}: {e}")
            continue
        
        print()  # Empty line between families
    
    print(f"\n{'='*60}")
    print(f"All plots saved to directory: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
