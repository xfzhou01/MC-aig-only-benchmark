#!/usr/bin/env python3
"""
Analyze different family combinations to find the best visualization.
"""

import os
import sys
from itertools import combinations
from parse_aig_list import parse_aig_list
from parse_ric3_log import parse_ric3_log

def parse_log_directory(log_dir, parser_func):
    """Parse all log files in a directory."""
    results = {}
    
    if not os.path.exists(log_dir):
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


def analyze_family_combination(families, log_dir1, log_dir2, results1, results2, aig_files_by_family):
    """
    Analyze a specific family combination.
    Returns statistics about this combination.
    """
    # Get all basenames for these families
    family_basenames = set()
    
    for family in families:
        if family in aig_files_by_family:
            for basename in aig_files_by_family[family]:
                # basename is already without .aig extension
                basename_clean = basename.replace('.aig', '')
                family_basenames.add(basename_clean)
    
    # Find common benchmarks that exist in both log directories
    common = family_basenames & set(results1.keys()) & set(results2.keys())
    
    if len(common) == 0:
        return None
    
    # Collect statistics
    solved1_total = 0
    solved2_total = 0
    solved1_100s = 0
    solved2_100s = 0
    solved1_1000s = 0
    solved2_1000s = 0
    
    time_ranges = {
        'very_fast': 0,    # < 10s
        'fast': 0,         # 10-100s
        'medium': 0,       # 100-1000s
        'slow': 0,         # 1000-3600s
        'timeout': 0       # = 3600s
    }
    
    for basename in common:
        time1, _, result1 = results1[basename]
        time2, _, result2 = results2[basename]
        
        # Count solved (not timeout)
        if time1 < 3600:
            solved1_total += 1
        if time2 < 3600:
            solved2_total += 1
            
        # Count solved within 100s
        if time1 <= 100:
            solved1_100s += 1
        if time2 <= 100:
            solved2_100s += 1
            
        # Count solved within 1000s
        if time1 <= 1000:
            solved1_1000s += 1
        if time2 <= 1000:
            solved2_1000s += 1
        
        # Categorize by time range (use average of both solvers)
        avg_time = (time1 + time2) / 2
        if avg_time < 10:
            time_ranges['very_fast'] += 1
        elif avg_time < 100:
            time_ranges['fast'] += 1
        elif avg_time < 1000:
            time_ranges['medium'] += 1
        elif avg_time < 3600:
            time_ranges['slow'] += 1
        else:
            time_ranges['timeout'] += 1
    
    # Calculate improvement statistics
    solver2_better = 0
    solver1_better = 0
    both_timeout = 0
    
    for basename in common:
        time1, _, result1 = results1[basename]
        time2, _, result2 = results2[basename]
        
        if time1 >= 3600 and time2 >= 3600:
            both_timeout += 1
        elif time2 < time1:
            solver2_better += 1
        elif time1 < time2:
            solver1_better += 1
    
    improvement_ratio = solver2_better / len(common) if len(common) > 0 else 0
    
    return {
        'families': families,
        'total_cases': len(common),
        'solved1_total': solved1_total,
        'solved2_total': solved2_total,
        'solved1_100s': solved1_100s,
        'solved2_100s': solved2_100s,
        'solved1_1000s': solved1_1000s,
        'solved2_1000s': solved2_1000s,
        'difference_total': solved2_total - solved1_total,
        'difference_100s': solved2_100s - solved1_100s,
        'difference_1000s': solved2_1000s - solved1_1000s,
        'time_ranges': time_ranges,
        'diversity_score': time_ranges['fast'] + time_ranges['medium'] + time_ranges['slow'],
        'solver2_better': solver2_better,
        'solver1_better': solver1_better,
        'both_timeout': both_timeout,
        'improvement_ratio': improvement_ratio
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python analyze_family_combinations.py <log_dir1> <log_dir2>")
        sys.exit(1)
    
    log_dir1 = sys.argv[1]
    log_dir2 = sys.argv[2]
    
    # Define directory mappings for merged experiments
    dir_mappings = {
        'hpc_ric3_dyn_2025': ['hpc_ric3_dyn_2025', 'hpc_ric3_sl_dynamic'],
        'hpc_ric3_sl_dynamic': ['hpc_ric3_sl_dynamic', 'hpc_ric3_dyn_2025'],
        'hpc_ric3_mab_2025': ['hpc_ric3_mab_2025', 'hpc_ric3_sl_mab_6_add_context_and_reward_decay070'],
        'hpc_ric3_sl_mab_6_add_context_and_reward_decay070': ['hpc_ric3_sl_mab_6_add_context_and_reward_decay070', 'hpc_ric3_mab_2025']
    }
    
    # Get directories to parse (with merging)
    dirs1 = dir_mappings.get(log_dir1, [log_dir1])
    dirs2 = dir_mappings.get(log_dir2, [log_dir2])
    
    print(f"Analyzing family combinations for:")
    print(f"  Solver 1: {log_dir1}")
    if len(dirs1) > 1:
        print(f"    Merged with: {', '.join(dirs1[1:])}")
    print(f"  Solver 2: {log_dir2}")
    if len(dirs2) > 1:
        print(f"    Merged with: {', '.join(dirs2[1:])}")
    print()
    
    # Parse all logs (merged)
    print("Parsing logs...")
    results1 = parse_log_directories(dirs1, parse_ric3_log)
    results2 = parse_log_directories(dirs2, parse_ric3_log)
    print(f"  {log_dir1}: {len(results1)} logs (merged)")
    print(f"  {log_dir2}: {len(results2)} logs (merged)")
    print()
    
    # Get all families
    aig_files_by_family, basename_to_paths = parse_aig_list('aig_files_list.txt')
    all_families = list(aig_files_by_family.keys())
    print(f"Found {len(all_families)} families:")
    for f in all_families:
        print(f"  - {f}")
    print()
    
    # Analyze individual families first
    print("=" * 80)
    print("INDIVIDUAL FAMILIES")
    print("=" * 80)
    
    individual_results = []
    for family in all_families:
        result = analyze_family_combination([family], log_dir1, log_dir2, results1, results2, aig_files_by_family)
        if result:
            individual_results.append(result)
    
    # Calculate difference ratio and add to results
    for r in individual_results:
        r['diff_ratio'] = abs(r['difference_total']) / r['total_cases'] if r['total_cases'] > 0 else 0
    
    # Sort by difference ratio (higher is better)
    individual_results.sort(key=lambda x: x['diff_ratio'], reverse=True)
    
    print(f"\n{'Family':<20} {'Total':<7} {'Diff':<6} {'DiffRatio':<10} {'S2>S1':<8} {'ImpRatio':<10} {'<100s':<10} {'<1000s':<10}")
    print("-" * 110)
    for r in individual_results:
        family_name = r['families'][0]
        print(f"{family_name:<20} {r['total_cases']:<7} {r['difference_total']:+6} "
              f"{r['diff_ratio']*100:>6.2f}%  "
              f"{r['solver2_better']:<8} {r['improvement_ratio']*100:>5.1f}%  "
              f"{r['solved2_100s']:>3}/{r['solved1_100s']:<3} "
              f"{r['solved2_1000s']:>3}/{r['solved1_1000s']:<3}")
    
    # Analyze multi-family combinations (must include hwmcc24 and hwmcc2025)
    required_families = {'hwmcc24', 'hwmcc2025'}
    other_families = [f for f in all_families if f not in required_families]
    
    for n_additional in [0, 1, 2, 3]:
        n_families = 2 + n_additional  # 2 required + additional
        print("\n" + "=" * 120)
        print(f"{n_families}-FAMILY COMBINATIONS (hwmcc24 + hwmcc2025 + {n_additional} others, Top 20 by difference ratio)")
        print("=" * 120)
        
        multi_family_results = []
        
        if n_additional == 0:
            # Just the two required families
            families = list(required_families)
            result = analyze_family_combination(families, log_dir1, log_dir2, results1, results2, aig_files_by_family)
            if result and result['total_cases'] >= 50:
                result['diff_ratio'] = abs(result['difference_total']) / result['total_cases'] if result['total_cases'] > 0 else 0
                multi_family_results.append(result)
        else:
            # Required families + combinations of others
            for additional in combinations(other_families, n_additional):
                families = list(required_families) + list(additional)
                result = analyze_family_combination(families, log_dir1, log_dir2, results1, results2, aig_files_by_family)
                if result and result['total_cases'] >= 50:
                    result['diff_ratio'] = abs(result['difference_total']) / result['total_cases'] if result['total_cases'] > 0 else 0
                    multi_family_results.append(result)
        
        multi_family_results.sort(key=lambda x: x['diff_ratio'], reverse=True)
        
        print(f"\n{'Families':<55} {'Total':<7} {'Diff':<6} {'DiffRatio':<10} {'S2>S1':<8} {'ImpRatio':<10}")
        print("-" * 105)
        for r in multi_family_results[:20]:
            family_names = '+'.join(sorted(r['families']))
            if len(family_names) > 55:
                family_names = family_names[:52] + '...'
            print(f"{family_names:<55} {r['total_cases']:<7} {r['difference_total']:+6} "
                  f"{r['diff_ratio']*100:>6.2f}%  "
                  f"{r['solver2_better']:<8} {r['improvement_ratio']*100:>5.1f}%")
    
    # Find best combinations by different criteria
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    # Best by difference ratio
    best_diff_ratio = individual_results[0]  # Already sorted by diff_ratio
    print(f"\n1. Highest difference ratio (difference/total):")
    print(f"   Families: {', '.join(best_diff_ratio['families'])}")
    print(f"   Total cases: {best_diff_ratio['total_cases']}")
    print(f"   Difference: {best_diff_ratio['difference_total']:+d}")
    print(f"   Difference ratio: {best_diff_ratio['diff_ratio']*100:.2f}%")
    
    # Best by absolute difference
    best_abs_diff = max(individual_results, key=lambda x: abs(x['difference_total']))
    print(f"\n2. Largest absolute difference:")
    print(f"   Families: {', '.join(best_abs_diff['families'])}")
    print(f"   Total cases: {best_abs_diff['total_cases']}")
    print(f"   Difference: {best_abs_diff['difference_total']:+d}")
    print(f"   Difference ratio: {best_abs_diff['diff_ratio']*100:.2f}%")
    
    # Best by diversity (interesting time ranges)
    best_diversity = max(individual_results, key=lambda x: x['diversity_score'])
    print(f"\n3. Best diversity (most cases in 10s-3600s range):")
    print(f"   Families: {', '.join(best_diversity['families'])}")
    print(f"   Total cases: {best_diversity['total_cases']}")
    print(f"   Diversity score: {best_diversity['diversity_score']}")
    print(f"   Time distribution: fast={best_diversity['time_ranges']['fast']}, "
          f"medium={best_diversity['time_ranges']['medium']}, slow={best_diversity['time_ranges']['slow']}")


if __name__ == '__main__':
    main()
