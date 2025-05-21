import os
import re
import numpy as np
import random
import shutil
import glob
import sys

def extract_time_and_arm_pulls(folder):
    result = {}
    for fname in os.listdir(folder):
        if not fname.endswith('.txt'):
            continue
        path = os.path.join(folder, fname)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 优先用 case 字段，否则用文件名
        m_bench = re.search(r'case:\s*([^\s,]+)', content)
        if m_bench:
            bench = m_bench.group(1)
        else:
            bench = fname.replace('_log.txt', '').replace('.txt', '')
        # 判断是否超时
        if "STATUS: TIMEOUT" in content or "exceeded 3600 seconds" in content or "TIMEOUT" in content:
            solve_time = 3600.0
        else:
            m_time = re.search(r'time:\s*([\d.]+)s', content)
            if not m_time:
                continue
            solve_time = float(m_time.group(1))
        # 提取 arm pulls
        arm_section = re.search(r'Arm pulls:(.*?)(?:-+|SolverStatistic|Statistic|result:)', content, re.DOTALL)
        pulls = []
        if arm_section:
            arm_lines = arm_section.group(1).strip().splitlines()
            for line in arm_lines:
                match = re.match(r'\s*Arm\s+\d+\s*\(.*?\):\s*(\d+)\s+pulls', line)
                if match:
                    pulls.append(int(match.group(1)))
        if not pulls:
            pulls = [0]
        # 提取 aig 文件名
        m_aig = re.search(r'File:\s*(.*\.aig)', content)
        if m_aig:
            aig_file = m_aig.group(1).strip()
        else:
            aig_file = bench if bench.endswith('.aig') else bench + '.aig'
        result[bench] = (solve_time, pulls, aig_file)
    return result

def sample_benchmarks_weighted(result_dict, num_samples=1):
    keys = np.array(list(result_dict.keys()))
    times = np.array([result_dict[k][0] for k in keys])
    min_time = np.min(times[times > 0]) if np.any(times > 0) else 1e-6
    weights = np.where(times > 0, times, min_time)
    probs = weights / weights.sum()
    if num_samples > len(keys):
        num_samples = len(keys)
    sampled_keys = np.random.choice(keys, size=num_samples, replace=False, p=probs)
    sampled_result = {k: result_dict[k] for k in sampled_keys}
    return sampled_result

# 用法示例
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sample.py <dst_folder>")
        sys.exit(1)
    dst_folder = sys.argv[1]

    folder = "/home/x/xiaofeng-zhou/MC-aig-only-benchmark/rIC3_solver_mab2_logs"
    aig_root = "/home/x/xiaofeng-zhou/MC-aig-only-benchmark"
    result = extract_time_and_arm_pulls(folder)
    print(f"Extracted {len(result)} items from {folder}.")
    # 采样非超时的
    sampled_result = sample_benchmarks_weighted(result, num_samples=150)
    print(f"Sampled {len(sampled_result)} non-timeout items.")
    # 找出所有超时的，且不在已采样结果中
    timeout_items = [(bench, v) for bench, v in result.items() if v[0] == 3600 and bench not in sampled_result]
    print(f"Found {len(timeout_items)} timeout items.")
    # 随机采样50个超时的
    if len(timeout_items) > 50:
        timeout_items = random.sample(timeout_items, 50)
    print(f"Randomly sampled {len(timeout_items)} timeout items.")
    # 合并到sampled_result
    for bench, (solve_time, pulls, aig_file) in timeout_items:
        sampled_result[bench] = (solve_time, pulls, aig_file)

    # 拷贝aig文件
    os.makedirs(dst_folder, exist_ok=True)
    for bench, (solve_time, pulls, aig_file) in sampled_result.items():
        src_path = os.path.join(aig_root, aig_file) if not os.path.isabs(aig_file) else aig_file
        if os.path.exists(src_path):
            shutil.copy(src_path, dst_folder)
        else:
            print(f"Warning: {src_path} not found.")

    print(f"Copied {len(sampled_result)} files to {dst_folder}")

