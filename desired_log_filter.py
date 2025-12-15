import os

def read_log_files(target_folder):
    log_files = [f for f in os.listdir(target_folder) if f.endswith('.log')]
    for log_file in log_files:
        file_path = os.path.join(target_folder, log_file)
        with open(file_path, 'r') as file:
            print(f"Contents of {log_file}:")
            print(file.read())

def has_time_in_range(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if "time:" in line and line.startswith("time:"):
                parts = line.split("time:")
                if len(parts) > 1:
                    try:
                        time_value = float(parts[1].strip().rstrip('s')[:-2])
                        if 100 <= time_value <= 1000:
                            return True
                    except ValueError:
                        print(f"Could not convert time value to float in line: {line.strip()}")
                        continue
    return False
def check_logs_for_time(target_folder):
    log_files = [f for f in os.listdir(target_folder) if f.endswith('.txt')]
    for log_file in log_files:
        file_path = os.path.join(target_folder, log_file)
        if has_time_in_range(file_path):
            # print(f"{log_file} contains a time value in the range 50-200 seconds.")
            print(log_file.split(".txt")[0].split("_log")[0])
        # else:
        #     print(f"{log_file} does not contain a time value in the range 50-200 seconds.")


# Example usage
print("Reading log files:")
target_folder = '/home/x/xiaofeng-zhou/MC-aig-only-benchmark/rIC3_solver_dynamic_logs'
check_logs_for_time(target_folder)