#!/bin/bash

# Stability Audit Orchestrator
# ============================
# Runs all stability audit tests and generates report.
#
# Usage:
#   ./run-all-audits.sh [OPTIONS]
#
# Options:
#   --target URL          API target (default: http://localhost:8000)
#   --timeout SECONDS     Request timeout (default: 120)
#   --report FILE         Generate HTML report (optional)
#   --verbose             Verbose output
#   --json                JSON output only
#   --help                Show this help

set -e

# Defaults
TARGET="http://localhost:8000"
TIMEOUT=120
REPORT=""
VERBOSE=false
JSON=false
HELP=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --target)
            TARGET="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --report)
            REPORT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --json)
            JSON=true
            shift
            ;;
        --help)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Show help
if [ "$HELP" = true ]; then
    head -n 20 "$0" | tail -n 16
    exit 0
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="${SCRIPT_DIR}/results-${TIMESTAMP}"

# Create results directory
mkdir -p "$RESULTS_DIR"

# Build common options
COMMON_OPTS="--target $TARGET --timeout $TIMEOUT"
if [ "$VERBOSE" = true ]; then
    COMMON_OPTS="$COMMON_OPTS --verbose"
fi

# Header
if [ "$JSON" != true ]; then
    echo ""
    echo "======================================================================"
    echo "  STABILITY AUDIT TOOLKIT"
    echo "======================================================================"
    echo "Target:     $TARGET"
    echo "Timeout:    ${TIMEOUT}s"
    echo "Results:    $RESULTS_DIR"
    echo ""
fi

# Run all tests
declare -a TESTS=(
    "test-boundaries.py"
    "test-error-handling.py"
)

TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_ERRORS=0
TEST_RESULTS=()

for test in "${TESTS[@]}"; do
    TEST_NAME="${test%.py}"
    RESULTS_FILE="${RESULTS_DIR}/${TEST_NAME}-results.json"
    
    if [ "$JSON" = true ]; then
        # JSON mode: run test and capture JSON output
        python "$SCRIPT_DIR/$test" $COMMON_OPTS --json > "$RESULTS_FILE" 2>&1 || true
    else
        # Normal mode: run test and capture output
        echo "[Running] $TEST_NAME"
        python "$SCRIPT_DIR/$test" $COMMON_OPTS > "$RESULTS_FILE.txt" 2>&1 || true
        
        # Extract summary stats from output
        if grep -q "PASS\|FAIL" "$RESULTS_FILE.txt"; then
            echo "  ✓ Completed"
        else
            echo "  ⚠ No results"
        fi
    fi
    
    TEST_RESULTS+=("$RESULTS_FILE")
done

# Generate summary report if requested
if [ -n "$REPORT" ]; then
    if [ "$JSON" != true ]; then
        echo ""
        echo "[Report] Generating $REPORT..."
    fi
    
    # Create basic HTML report
    cat > "$REPORT" <<'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Stability Audit Report</title>
    <style>
        body { font-family: monospace; margin: 20px; }
        h1 { color: #333; }
        .summary { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .pass { color: green; font-weight: bold; }
        .fail { color: red; font-weight: bold; }
        .error { color: orangered; font-weight: bold; }
        .test-group { margin: 20px 0; padding: 10px; border-left: 4px solid #ddd; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f9f9f9; }
    </style>
</head>
<body>
    <h1>Stability Audit Report</h1>
    <div class="summary">
        <p><strong>Generated:</strong> TIMESTAMP_PLACEHOLDER</p>
        <p><strong>Target:</strong> TARGET_PLACEHOLDER</p>
    </div>
    <h2>Results</h2>
    <p>Individual test results saved to: RESULTS_DIR_PLACEHOLDER</p>
    <h3>Files Generated</h3>
    <ul>
        RESULTS_PLACEHOLDER
    </ul>
    <p><strong>Instructions:</strong> Review individual JSON files in results directory for detailed test output.</p>
</body>
</html>
EOF
    
    # Replace placeholders
    sed -i "s|TIMESTAMP_PLACEHOLDER|$(date)|g" "$REPORT"
    sed -i "s|TARGET_PLACEHOLDER|$TARGET|g" "$REPORT"
    sed -i "s|RESULTS_DIR_PLACEHOLDER|$RESULTS_DIR|g" "$REPORT"
    
    # Add file list
    FILE_LIST=""
    for result_file in "${TEST_RESULTS[@]}"; do
        FILE_LIST="$FILE_LIST        <li><a href=\"$(basename "$result_file")\">$(basename "$result_file")</a></li>\n"
    done
    sed -i "s|RESULTS_PLACEHOLDER|$FILE_LIST|g" "$REPORT"
fi

# Print summary
if [ "$JSON" != true ]; then
    echo ""
    echo "======================================================================"
    echo "  AUDIT COMPLETE"
    echo "======================================================================"
    echo "Results saved to: $RESULTS_DIR"
    echo ""
    echo "To review results:"
    echo "  cat $RESULTS_DIR/*.txt"
    echo ""
    if [ -n "$REPORT" ]; then
        echo "Report generated: $REPORT"
    fi
fi

exit 0
