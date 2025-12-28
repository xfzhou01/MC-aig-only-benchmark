#!/usr/bin/env python3
"""
Script to parse rIC3 log files and extract time/array length/result type.
For successful cases: returns actual time and array length along with proof/cex flag.
For timeout cases: returns 3600, -1, and marks the result as unknown.
"""

import os
import re
from datetime import datetime


def parse_ric3_log(log_file_path):
    """
    Parse rIC3 log file to extract execution time, array length, result type, and level.
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        tuple: (time in seconds, array length, result_type, level)
               result_type ∈ {"proof", "counter-example", "unknown"}
               level: the length of the array (induction depth)
               For timeout: (3600, -1, "unknown", -1) unless a result is explicitly logged
    """
    if not os.path.exists(log_file_path):
        raise FileNotFoundError(f"Log file not found: {log_file_path}")
    
    with open(log_file_path, 'r') as f:
        content = f.read()

    # Determine solver result before returning early for timeouts.
    result_match = re.search(r'result:\s*(\w+)', content, re.IGNORECASE)
    result_token = result_match.group(1).lower() if result_match else None
    if result_token == 'safe':
        result_type = 'proof'
    elif result_token == 'unsafe':
        result_type = 'counter-example'
    else:
        result_type = 'unknown'
    
    # Look for the array pattern like [0, 0, 0, 0, ..., 2232] or []
    array_pattern = r'\[[\d,\s]*\]'
    array_match = re.search(array_pattern, content)
    
    # If no array found, treat it as a timeout/unknown length case
    if not array_match:
        return 3600, -1, result_type, -1
    
    # Extract array and get its length
    array_str = array_match.group(0)
    # Parse the array string to get actual list
    array_content = array_str.strip('[]').strip()
    if not array_content:
        # Empty array
        array_length = 0
        level = 0
    else:
        array_values = [int(x.strip()) for x in array_content.split(',') if x.strip()]
        array_length = len(array_values)
        level = array_length  # Level is the array length (induction depth)
    
    # Extract time from "time: X.XXs" pattern in Statistic section
    time_pattern = r'time:\s*([\d.]+)s'
    time_match = re.search(time_pattern, content)
    
    if time_match:
        time_seconds = float(time_match.group(1))
    else:
        # Fallback: calculate from start and finish timestamps
        start_pattern = r'Started at:\s*(.+)'
        finish_pattern = r'Finished at:\s*(.+)'
        
        start_match = re.search(start_pattern, content)
        finish_match = re.search(finish_pattern, content)
        
        if start_match and finish_match:
            start_time_str = start_match.group(1).strip()
            finish_time_str = finish_match.group(1).strip()
            
            # Parse timestamps (format: "Tue Jun 10 04:16:20 CST 2025")
            time_format = "%a %b %d %H:%M:%S CST %Y"
            try:
                start_time = datetime.strptime(start_time_str, time_format)
                finish_time = datetime.strptime(finish_time_str, time_format)
                time_seconds = (finish_time - start_time).total_seconds()
            except ValueError:
                # If parsing fails, return timeout values
                return 3600, -1, result_type, -1
        else:
            return 3600, -1, result_type, -1
    
    return time_seconds, array_length, result_type, level


def parse_ric3_log_batch(log_dir):
    """
    Parse all log files in a directory.
    
    Args:
        log_dir: Directory containing log files
        
    Returns:
        dict: Mapping from filename to (time, array_length, result_type, level) tuple
    """
    results = {}
    
    if not os.path.exists(log_dir):
        raise FileNotFoundError(f"Directory not found: {log_dir}")
    
    for filename in os.listdir(log_dir):
        if filename.endswith('_log.txt'):
            log_path = os.path.join(log_dir, filename)
            try:
                time, length, result_type, level = parse_ric3_log(log_path)
                results[filename] = (time, length, result_type, level)
            except Exception as e:
                print(f"Error parsing {filename}: {e}")
                results[filename] = (3600, -1, 'unknown', -1)
    
    return results


def main():
    """
    Example usage of the parsing functions.
    """
    # Test with the two example files
    example_success = "/home/x/xiaofeng-zhou/MC-aig-only-benchmark/hpc_ric3_sl_mab_6_add_context_and_reward/6s2_log.txt"
    example_timeout = "/home/x/xiaofeng-zhou/MC-aig-only-benchmark/hpc_ric3_sl_mab_6_add_context_and_reward/6s1_log.txt"
    
    print("Testing log parser:")
    print("=" * 60)
    
    # Parse successful case
    if os.path.exists(example_success):
        time, length, result_type, level = parse_ric3_log(example_success)
        print(f"\nSuccess case: 6s2_log.txt")
        print(f"  Time: {time}s")
        print(f"  Array length: {length}")
        print(f"  Result: {result_type}")
        print(f"  Level: {level}")
    
    # Parse timeout case
    if os.path.exists(example_timeout):
        time, length, result_type, level = parse_ric3_log(example_timeout)
        print(f"\nTimeout case: 6s1_log.txt")
        print(f"  Time: {time}s")
        print(f"  Array length: {length}")
        print(f"  Result: {result_type}")
        print(f"  Level: {level}")
    
    # Parse batch of logs in the directory
    log_dir = "/home/x/xiaofeng-zhou/MC-aig-only-benchmark/hpc_ric3_sl_mab_6_add_context_and_reward"
    if os.path.exists(log_dir):
        print(f"\n{'=' * 60}")
        print(f"Parsing all logs in directory (first 10):")
        print("=" * 60)
        results = parse_ric3_log_batch(log_dir)
        
        # Show all results
        for filename, (time, length, result_type, level) in sorted(results.items()):
            print(f"{filename:40s} -> time: {time:8.2f}s, length: {length:5d}, result: {result_type}, level: {level:5d}")
        
        print(f"\n{'=' * 60}")
        print(f"Total logs parsed: {len(results)}")
        success_count = sum(1 for _, (_, length, _) in results.items() if length != -1)
        timeout_count = len(results) - success_count
        print(f"  Successful: {success_count}")
        print(f"  Timeout: {timeout_count}")


if __name__ == "__main__":
    main()
