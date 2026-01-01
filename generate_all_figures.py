#!/usr/bin/env python3
"""
Comprehensive script to generate all figures and tables for CAV submission.

This script generates:
- 2 cactus plots (rIC3 and IC3REF) for hwmcc202425
- PAR-2 tables (rIC3 and IC3REF) for hwmcc202425
- 3 rIC3 time scatter plots (3 comparisons, log scale)
- 2 IC3REF time scatter plots (2 comparisons, log scale)
- 3 rIC3 level scatter plots (3 comparisons)
- 2 IC3REF level scatter plots (2 comparisons)

All outputs are saved to cav_fig_N/ directory (N is auto-incremented).
Intermediate files are cleaned up automatically.

Usage:
    python generate_all_figures.py

Configuration:
    To change the data folders being analyzed, modify the RIC3_SOLVER_DIRS
    and IC3REF_SOLVER_DIRS dictionaries in the configuration section below.
    All scripts will automatically use these centralized settings.
"""

import os
import sys
import glob
import shutil
import subprocess


# ============================================================================
#  DATA FOLDER CONFIGURATION - MODIFY HERE TO CHANGE ALL DATA PATHS
# ============================================================================

# rIC3 solver log directories
RIC3_SOLVER_DIRS = {
    'standard': 'hpc_ric3_ic3_pure_20251221_redo',
    'ctgdown': 'hpc_ric3_ic3_ctgdown_20251221_redo',
    'dynamic': 'hpc_ric3_dyn_20251221_redo',
    'mab': 'hpc_ric3_ic3_mab_20251221_redo'
}

# IC3REF solver log directories
IC3REF_SOLVER_DIRS = {
    'standard': 'hpc_IC3REF_basic_20251219_redo',
    'ctgdown': 'hpc_IC3REF_ctgdown_20251219_redo',
    'mab': 'hpc_IC3REF_mab_20251230_alpha_1_redo'
}

# Test families to analyze
FAMILIES = "hwmcc20,hwmcc24,hwmcc2025"

# ============================================================================

# Derived configurations (DO NOT MODIFY - auto-generated from above)
RIC3_SOLVERS = [
    [RIC3_SOLVER_DIRS['dynamic']],
    [RIC3_SOLVER_DIRS['mab']],
    [RIC3_SOLVER_DIRS['standard']],
    [RIC3_SOLVER_DIRS['ctgdown']]
]

IC3REF_SOLVERS = [
    [IC3REF_SOLVER_DIRS['standard']],
    [IC3REF_SOLVER_DIRS['mab']],
    [IC3REF_SOLVER_DIRS['ctgdown']]
]

# Solver pairs for comparison (solver1 on Y-axis, solver2 on X-axis)
# MAB should be on Y-axis, so MAB is solver1
RIC3_COMPARE_PAIRS = [
    (RIC3_SOLVER_DIRS['mab'], RIC3_SOLVER_DIRS['dynamic']),
    (RIC3_SOLVER_DIRS['mab'], RIC3_SOLVER_DIRS['standard']),
    (RIC3_SOLVER_DIRS['mab'], RIC3_SOLVER_DIRS['ctgdown'])
]

IC3REF_COMPARE_PAIRS = [
    (IC3REF_SOLVER_DIRS['mab'], IC3REF_SOLVER_DIRS['standard']),
    (IC3REF_SOLVER_DIRS['mab'], IC3REF_SOLVER_DIRS['ctgdown'])
]


def get_solver_short_name(solver_dir):
    """Get short name for solver directory."""
    if 'ic3_mab' in solver_dir:
        return 'rIC3-MAB'
    elif 'ic3_pure' in solver_dir:
        return 'rIC3-Standard'
    elif 'ic3_ctgdown' in solver_dir or 'ric3_ctg' in solver_dir:
        return 'rIC3-CtgDown'
    elif 'ric3_dyn' in solver_dir:
        return 'rIC3-DynAMic'
    elif 'IC3REF_mab' in solver_dir:
        return 'IC3Ref-MAB'
    elif 'IC3REF_basic' in solver_dir:
        return 'IC3Ref-Standard'
    elif 'IC3REF_ctgdown' in solver_dir:
        return 'IC3Ref-CtgDown'
    else:
        return solver_dir


def find_next_cav_fig_number():
    """Find the next available cav_fig_N number."""
    existing = glob.glob('cav_fig_*')
    if not existing:
        return 1
    
    numbers = []
    for dirname in existing:
        try:
            num = int(dirname.replace('cav_fig_', ''))
            numbers.append(num)
        except ValueError:
            continue
    
    return max(numbers) + 1 if numbers else 1


def run_command(cmd, description):
    """Run a command and print status."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {description} failed!")
        print(result.stderr)
        return False
    
    print(result.stdout)
    return True


def generate_cactus_plots(output_dir):
    """Generate cactus plots for rIC3 and IC3REF."""
    print("\n" + "="*70)
    print("  GENERATING CACTUS PLOTS")
    print("="*70)
    
    # rIC3 cactus plot
    ric3_cmd = ['python3', 'generate_cactus_plot_by_family.py']
    for solver_dirs in RIC3_SOLVERS:
        ric3_cmd.extend(['--solver'] + solver_dirs)
    ric3_cmd.extend(['--families', FAMILIES, '--parser', 'ric3'])
    
    if not run_command(ric3_cmd, "Generating rIC3 cactus plot"):
        return False
    
    # IC3REF cactus plot
    ic3ref_cmd = ['python3', 'generate_cactus_plot_by_family.py']
    for solver_dirs in IC3REF_SOLVERS:
        ic3ref_cmd.extend(['--solver'] + solver_dirs)
    ic3ref_cmd.extend(['--families', FAMILIES, '--parser', 'ic3ref'])
    
    if not run_command(ic3ref_cmd, "Generating IC3REF cactus plot"):
        return False
    
    # Move cactus plots
    cactus_files = glob.glob('plots_*/*.png') + glob.glob('plots_*/*.pdf')
    for f in cactus_files:
        basename = os.path.basename(f)
        shutil.move(f, os.path.join(output_dir, basename))
        print(f"  Moved: {basename}")
    
    return True


def generate_par2_tables(output_dir):
    """Generate PAR-2 tables for rIC3 and IC3REF."""
    print("\n" + "="*70)
    print("  GENERATING PAR-2 TABLES")
    print("="*70)
    
    # rIC3 PAR-2 table
    ric3_cmd = ['python3', 'generate_par2_table.py',
                '--standard', RIC3_SOLVER_DIRS['standard'],
                '--ctgdown', RIC3_SOLVER_DIRS['ctgdown'],
                '--dynamic', RIC3_SOLVER_DIRS['dynamic'],
                '--mab', RIC3_SOLVER_DIRS['mab']]
    if not run_command(ric3_cmd, "Generating rIC3 PAR-2 table"):
        return False
    
    # IC3REF PAR-2 table
    ic3ref_cmd = ['python3', 'generate_par2_table.py', '--ic3ref',
                  '--standard', IC3REF_SOLVER_DIRS['standard'],
                  '--ctgdown', IC3REF_SOLVER_DIRS['ctgdown'],
                  '--mab', IC3REF_SOLVER_DIRS['mab']]
    if not run_command(ic3ref_cmd, "Generating IC3REF PAR-2 table"):
        return False
    
    # Move CSV files
    csv_files = glob.glob('par2_table_*.csv')
    for f in csv_files:
        basename = os.path.basename(f)
        shutil.move(f, os.path.join(output_dir, basename))
        print(f"  Moved: {basename}")
    
    return True


def generate_time_scatter_plots(output_dir):
    """Generate time scatter plots for rIC3 and IC3REF."""
    print("\n" + "="*70)
    print("  GENERATING TIME SCATTER PLOTS")
    print("="*70)
    
    # rIC3 scatter plots
    for solver1, solver2 in RIC3_COMPARE_PAIRS:
        cmd = ['python3', 'compare_solvers_by_family.py', 
               solver1, solver2, FAMILIES, 'ric3']
        desc = f"rIC3 time scatter: {solver1} vs {solver2}"
        if not run_command(cmd, desc):
            return False
    
    # IC3REF scatter plots
    for solver1, solver2 in IC3REF_COMPARE_PAIRS:
        cmd = ['python3', 'compare_solvers_by_family.py', 
               solver1, solver2, FAMILIES, 'ic3ref']
        desc = f"IC3REF time scatter: {solver1} vs {solver2}"
        if not run_command(cmd, desc):
            return False
    
    # Move and rename scatter plots
    scatter_dirs = glob.glob('comparison_*')
    for dir_name in scatter_dirs:
        if '_level' in dir_name:  # Skip level directories for now
            continue
        
        # Extract solver names from directory
        # Format: comparison_solver1_vs_solver2
        parts = dir_name.replace('comparison_', '').split('_vs_')
        if len(parts) == 2:
            solver1_short = get_solver_short_name(parts[0])
            solver2_short = get_solver_short_name(parts[1])
            
            scatter_files = glob.glob(f'{dir_name}/*.png') + glob.glob(f'{dir_name}/*.pdf')
            for f in scatter_files:
                basename = os.path.basename(f)
                ext = '.pdf' if basename.endswith('.pdf') else '.png'
                new_name = f'{solver1_short}_vs_{solver2_short}_time{ext}'
                shutil.move(f, os.path.join(output_dir, new_name))
                print(f"  Moved: {new_name}")
    
    return True


def generate_level_scatter_plots(output_dir):
    """Generate level scatter plots for rIC3 and IC3REF."""
    print("\n" + "="*70)
    print("  GENERATING LEVEL SCATTER PLOTS")
    print("="*70)
    
    # rIC3 level scatter plots
    for solver1, solver2 in RIC3_COMPARE_PAIRS:
        cmd = ['python3', 'compare_solvers_level.py', 
               solver1, solver2, FAMILIES, 'ric3']
        desc = f"rIC3 level scatter: {solver1} vs {solver2}"
        if not run_command(cmd, desc):
            return False
    
    # IC3REF level scatter plots
    for solver1, solver2 in IC3REF_COMPARE_PAIRS:
        cmd = ['python3', 'compare_solvers_level.py', 
               solver1, solver2, FAMILIES, 'ic3ref']
        desc = f"IC3REF level scatter: {solver1} vs {solver2}"
        if not run_command(cmd, desc):
            return False
    
    # Move level scatter plots
    level_dirs = glob.glob('comparison_*_level')
    for dir_name in level_dirs:
        # Extract solver names from directory
        parts = dir_name.replace('comparison_', '').replace('_level', '').split('_vs_')
        if len(parts) == 2:
            solver1_short = get_solver_short_name(parts[0])
            solver2_short = get_solver_short_name(parts[1])
            
            level_files = glob.glob(f'{dir_name}/*.png') + glob.glob(f'{dir_name}/*.pdf')
            for f in level_files:
                ext = '.pdf' if f.endswith('.pdf') else '.png'
                new_name = f'{solver1_short}_vs_{solver2_short}_level{ext}'
                shutil.move(f, os.path.join(output_dir, new_name))
                print(f"  Moved: {new_name}")
    
    return True


def cleanup_intermediate_files():
    """Remove intermediate directories."""
    print("\n" + "="*70)
    print("  CLEANING UP INTERMEDIATE FILES")
    print("="*70)
    
    # Remove plots directories
    for d in glob.glob('plots_*'):
        shutil.rmtree(d)
        print(f"  Removed: {d}/")
    
    # Remove comparison directories
    for d in glob.glob('comparison_*'):
        shutil.rmtree(d)
        print(f"  Removed: {d}/")
    
    print("\nCleanup complete!")


def main():
    """Main function to generate all figures and tables."""
    print("="*70)
    print("  CAV Figure Generation Script")
    print("="*70)
    
    # Find next cav_fig number
    fig_num = find_next_cav_fig_number()
    output_dir = f'cav_fig_{fig_num}'
    
    print(f"\nOutput directory: {output_dir}/")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate all content
    steps = [
        (generate_cactus_plots, "Cactus plots"),
        (generate_par2_tables, "PAR-2 tables"),
        (generate_time_scatter_plots, "Time scatter plots"),
        (generate_level_scatter_plots, "Level scatter plots"),
    ]
    
    for func, name in steps:
        if not func(output_dir):
            print(f"\n❌ Error generating {name}")
            return 1
        print(f"\n✓ {name} completed successfully")
    
    # Cleanup
    cleanup_intermediate_files()
    
    # Summary
    print("\n" + "="*70)
    print("  GENERATION COMPLETE")
    print("="*70)
    print(f"\nAll figures saved to: {output_dir}/")
    
    # Count files
    png_files = glob.glob(f'{output_dir}/*.png')
    pdf_files = glob.glob(f'{output_dir}/*.pdf')
    csv_files = glob.glob(f'{output_dir}/*.csv')
    
    print(f"\nGenerated files:")
    print(f"  - PNG images: {len(png_files)}")
    print(f"  - PDF images: {len(pdf_files)}")
    print(f"  - CSV tables: {len(csv_files)}")
    print(f"  - Total: {len(png_files) + len(pdf_files) + len(csv_files)}")
    
    print(f"\n✓ All done! Check {output_dir}/ for results.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
