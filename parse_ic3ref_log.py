#!/usr/bin/env python3
"""Utilities to parse IC3REF log files for runtime, array length, and result type."""

import os
import re
from datetime import datetime

TIMEOUT_SECONDS = 3600
TIME_FORMAT = "%a %b %d %H:%M:%S CST %Y"


def _parse_elapsed_time(content):
    """Return the last reported elapsed time or None if unavailable."""
    elapsed_matches = re.findall(r'Elapsed time:\s*([\d.]+)', content)
    if elapsed_matches:
        try:
            return float(elapsed_matches[-1])
        except ValueError:
            return None
    start_match = re.search(r'Started at:\s*(.+)', content)
    finish_match = re.search(r'Finished at:\s*(.+)', content)
    if start_match and finish_match:
        try:
            start_time = datetime.strptime(start_match.group(1).strip(), TIME_FORMAT)
            finish_time = datetime.strptime(finish_match.group(1).strip(), TIME_FORMAT)
            delta_seconds = (finish_time - start_time).total_seconds()
            if delta_seconds >= 0:
                return delta_seconds
        except ValueError:
            return None
    return None


def _parse_array_length(content):
    """Extract the last K value from IC3REF logs, which represents the induction depth."""
    # Find all occurrences of ". K:            <number>"
    k_matches = re.findall(r'\.\s+K:\s+(\d+)', content)
    if k_matches:
        # Return the last K value found
        return int(k_matches[-1])
    return -1


def _parse_result_type(content):
    """Map the trailing digit before the File line to the normalized result label."""
    result_match = re.search(r'\n\s*([01])\s*\nFile:', content)
    if not result_match:
        return 'unknown'
    return 'proof' if result_match.group(1) == '0' else 'counter-example'


def parse_ic3ref_log(log_file_path):
    """Parse a single IC3REF log file."""
    if not os.path.exists(log_file_path):
        raise FileNotFoundError(f"Log file not found: {log_file_path}")
    with open(log_file_path, 'r') as handle:
        content = handle.read()
    result_type = _parse_result_type(content)
    array_length = _parse_array_length(content)
    time_seconds = _parse_elapsed_time(content)
    if time_seconds is None or result_type == 'unknown':
        time_seconds = TIMEOUT_SECONDS
    return time_seconds, array_length, result_type


def parse_ic3ref_log_batch(log_dir):
    """Parse every *_log.txt file in the provided directory."""
    if not os.path.exists(log_dir):
        raise FileNotFoundError(f"Directory not found: {log_dir}")
    results = {}
    for filename in os.listdir(log_dir):
        if not filename.endswith('_log.txt'):
            continue
        log_path = os.path.join(log_dir, filename)
        try:
            results[filename] = parse_ic3ref_log(log_path)
        except Exception as exc:
            print(f"Error parsing {filename}: {exc}")
            results[filename] = (TIMEOUT_SECONDS, -1, 'unknown')
    return results


def main():
    """Demonstrate the parser on proof/unknown/counter-example samples and parse full directory."""
    print("=" * 70)
    print("Testing sample logs:")
    print("=" * 70)
    proof_log = "/home/x/xiaofeng-zhou/MC-aig-only-benchmark/hpc_IC3REF_mab_context_predecessor_history_no_average/6s0_log.txt"
    unknown_log = "/home/x/xiaofeng-zhou/MC-aig-only-benchmark/hpc_IC3REF_mab_context_predecessor_history_no_average/6s1_log.txt"
    cex_log = "/home/x/xiaofeng-zhou/MC-aig-only-benchmark/hpc_IC3REF_mab_context_predecessor_history_no_average/139442p1_log.txt"
    for label, path in (('proof', proof_log), ('unknown', unknown_log), ('cex', cex_log)):
        if os.path.exists(path):
            time_seconds, array_length, result = parse_ic3ref_log(path)
            print(f"{label:7s} -> time: {time_seconds:8.2f}s, K: {array_length:4d}, result: {result}")
    
    print("\n" + "=" * 70)
    print("Parsing full directory:")
    print("=" * 70)
    log_dir = "/home/x/xiaofeng-zhou/MC-aig-only-benchmark/hpc_IC3REF_mab_context_predecessor_history_no_average"
    if os.path.exists(log_dir):
        batch = parse_ic3ref_log_batch(log_dir)
        
        # Statistics
        proof_count = sum(1 for _, (_, _, r) in batch.items() if r == 'proof')
        cex_count = sum(1 for _, (_, _, r) in batch.items() if r == 'counter-example')
        unknown_count = sum(1 for _, (_, _, r) in batch.items() if r == 'unknown')
        
        print(f"Total logs parsed: {len(batch)}")
        print(f"  Proof:           {proof_count}")
        print(f"  Counter-example: {cex_count}")
        print(f"  Unknown:         {unknown_count}")
        
        # Statistics on K values
        unknown_with_k = [(f, t, k, r) for f, (t, k, r) in batch.items() if r == 'unknown' and k != -1]
        print(f"\n✓ Unknown cases that reached K>0 before timeout: {len(unknown_with_k)}/{unknown_count}")
        
        # Show K distribution for completed proofs
        proof_k_values = [k for _, (_, k, r) in batch.items() if r == 'proof' and k != -1]
        if proof_k_values:
            print(f"✓ Proof K range: min={min(proof_k_values)}, max={max(proof_k_values)}, avg={sum(proof_k_values)/len(proof_k_values):.1f}")
        
        # Show first 10 results as sample
        print("\n" + "=" * 70)
        print("Sample results (first 10):")
        print("=" * 70)
        for i, (filename, (time, k, result)) in enumerate(sorted(batch.items())[:10]):
            print(f"{filename:40s} -> time: {time:8.2f}s, K: {k:4d}, result: {result}")


if __name__ == "__main__":
    main()
