#!/bin/bash

# Script to recursively find all .aig and .aag files and run rIC3 solver on each
# with a timeout of 3600 seconds (1 hour) and configurable parallelism

# Default number of parallel jobs (use number of CPU cores)
PARALLEL_JOBS=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
PARALLEL_JOBS=1
# Read the variable from the temporary file
if [ -f $HOME/hosts_available.cfg ]; then
    HOSTS_AVAILABLE=$(cat "$HOME/hosts_available.cfg")
    CPU_HOSTS=$(grep "cpu" "$HOME/hosts_available.cfg")
    echo "Received hosts: $HOSTS_AVAILABLE"
    echo "cpu hosts: $CPU_HOSTS"
else
    echo "No variable found."
fi

CPU_HOSTS="bmcpu01 bmcpu02 bmcpu03 bmcpu05 bmcpu07 bmcpu08 bmcpu09 cpu02 cpu03 cpu04 cpu05 cpu07 cpu08 cpu09 cpu10"


# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -j|--jobs)
            PARALLEL_JOBS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [-j|--jobs N]"
            echo "  -j, --jobs N    Number of parallel jobs (default: number of CPU cores)"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo "Running with $PARALLEL_JOBS parallel jobs"

# Create a directory to store logs
LOG_DIR="hpc_IC3REF_ctgdown_20251219_redo"
mkdir -p "$LOG_DIR"

# Find all .aig and .aag files recursively
echo "Finding all AIGER files (.aig and .aag)..."
AIGER_FILES=$(find /hpc/home/cwb.xzhoubu/hwmcc20_24_25_aig_files  -name "*.aig" -o -name "*.aag")
TOTAL_FILES=$(echo "$AIGER_FILES" | wc -l)
echo "Found $TOTAL_FILES AIGER files."

# Counter for processed files
COUNTER=0
ACTIVE_JOBS=0

# Function to process a single file
process_file() {
    local FILE=$1
    local COUNTER=$2
    local TOTAL_FILES=$3
    
    # Extract filename without path and extension for log naming
    local FILENAME=$(basename "$FILE")
    local LOG_FILE="$LOG_DIR/${FILENAME%.*}_log.txt"
    
    #if [ -f "$LOG_FILE" ] && grep -q "time:" "$LOG_FILE"; then
    #    echo "Log file contains 'time:'. Exiting function."
    #    return 1  
    #fi
    
    echo "[$COUNTER/$TOTAL_FILES] Processing: $FILE"
    echo "Log will be saved to: $LOG_FILE"
    
    # Run rIC3 solver with timeout
    {
        # Run the solver with timeout and capture output
        echo "Started at: $(date)"
        ABSOLUTE_FILE=$(realpath "$FILE")
        #COMMAND="bsub -Ip -n 1 -m "$CPU_HOSTS" docker run --rm  -v "$ABSOLUTE_FILE":/root/model.aig 10.120.24.15:5000/jhinno/ric3:latest -e ic3 --ic3-dynamic /root/model.aig 2>&1"
        #bsub -Ip -n 1 -m "$CPU_HOSTS" docker run --rm  -v "$ABSOLUTE_FILE":/root/model.aig 10.120.24.15:5000/jhinno/ric3:latest -e ic3 --ic3-dynamic /root/model.aig 2>&1
	COMMAND="bsub -Ip -n 1 /hpc/home/cwb.xzhoubu/IC3ref/IC3 -s -mab -alpha 1.0 < "$ABSOLUTE_FILE" 2>&1"
        # actually, IC3REF can be executed on any CPU HOSTS can does not require any docker to be pulled there
        bsub -Ip -n 1 -m "$CPU_HOSTS"  "timeout 3600 /hpc/home/cwb.xzhoubu/IC3ref/IC3 -s   < "$ABSOLUTE_FILE"" 2>&1
        # bsub -Ip -n 1 -m "$CPU_HOSTS"  "timeout 3600 /hpc/home/cwb.xzhoubu/IC3ref/IC3 -s < "$ABSOLUTE_FILE"" 2>&1
	# bsub -Ip -n 1 -m "$CPU_HOSTS"  "timeout 3600 /hpc/home/cwb.xzhoubu/IC3ref/IC3 -s -b < "$ABSOLUTE_FILE"" 2>&1
	echo "File: $FILE"
        echo "$COMMAND"
        
        echo "----------------------------------------"
        # Check if the command timed out
        if [ $? -eq 124 ]; then
            echo "----------------------------------------"
            echo "STATUS: TIMEOUT (exceeded 3600 seconds)"
        else
            echo "----------------------------------------"
            echo "STATUS: COMPLETED"
        fi
        
        echo "Finished at: $(date)"
        echo "========================================"
    } > "$LOG_FILE"
    
    # Print progress (use flock to avoid interleaved output)
    {
        flock -x 200
        echo "Completed $COUNTER of $TOTAL_FILES files: $FILE"
        echo "----------------------------------------"
    } 200>"/tmp/rIC3_solver_lock"
}

# Create a lock file for synchronized output
touch "/tmp/rIC3_solver_lock"

# Process files in parallel with controlled concurrency
for FILE in $AIGER_FILES; do
    COUNTER=$((COUNTER + 1))
    
    # Wait if we've reached the maximum number of parallel jobs
    while [ $ACTIVE_JOBS -ge $PARALLEL_JOBS ]; do
        # Wait for any child process to finish
        wait -n 2>/dev/null || true
        ACTIVE_JOBS=$((ACTIVE_JOBS - 1))
    done
    echo "counter: $COUNTER" 
    # Process the file in the background
    process_file "$FILE" "$COUNTER" "$TOTAL_FILES" &
    ACTIVE_JOBS=$((ACTIVE_JOBS + 1))

    # Check the number of jobs in the queue
    while [ "$(bjobs | wc -l)" -gt 79 ]; do
        echo "Pending jobs exceed threshold: 80"
        sleep 1
    done

    # Sleep for a short time to avoid overwhelming the system
    sleep 2
done

# Wait for all remaining jobs to finish
wait

echo "All files processed. Logs are stored in the $LOG_DIR directory."

# Clean up
rm -f "/tmp/rIC3_solver_lock"
