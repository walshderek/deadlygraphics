#!/bin/bash
# DeadlyMusubi Launcher
# Automated launcher for Musubi Tuner with venv selection and OOM/NaN mitigation

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEADLYMUSUBI_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_BASE="$HOME/venvs"
CONFIG_NAME="cuda121_torch25_baseline"
PROJECT_NAME=""
DRY_RUN=false

# Print colored message
print_msg() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Show usage
usage() {
    cat << EOF
DeadlyMusubi Launcher - Musubi Tuner with optimized venv configurations

Usage: $0 [OPTIONS]

Options:
    -c, --config NAME       Venv configuration to use (default: cuda121_torch25_baseline)
    -p, --project NAME      Project name for training
    -v, --venv-path PATH    Custom venv base path (default: ~/venvs)
    -l, --list              List available configurations
    -d, --dry-run           Show what would be done without executing
    -h, --help              Show this help message

Available Configurations:
    cuda121_torch25_baseline        - Standard RTX 4080/4090 (16GB+)
    cuda121_torch25_fp8_aggressive  - Memory-optimized RTX 3060+ (12GB+)
    cuda118_torch20_legacy          - Legacy RTX 3080/3090

Examples:
    $0 --config cuda121_torch25_baseline --project my_character
    $0 --list
    $0 --config cuda121_torch25_fp8_aggressive --project test_run --dry-run

EOF
    exit 0
}

# List available configurations
list_configs() {
    print_msg "$BLUE" "Available DeadlyMusubi Configurations:"
    echo ""
    
    for config_file in "$DEADLYMUSUBI_ROOT/venv_configs"/*.txt; do
        if [ -f "$config_file" ]; then
            config_name=$(basename "$config_file" .txt)
            
            # Extract info from file comments
            target=$(grep "# Target:" "$config_file" | sed 's/# Target: //')
            status=$(grep "# Status:" "$config_file" | sed 's/# Status: //')
            
            echo "  $config_name"
            echo "    Target: $target"
            echo "    Status: $status"
            echo ""
        fi
    done
    
    exit 0
}

# Check if venv exists
check_venv() {
    local venv_name=$1
    local venv_path="$VENV_BASE/$venv_name"
    
    if [ ! -d "$venv_path" ]; then
        print_msg "$YELLOW" "Virtual environment '$venv_name' not found at $venv_path"
        print_msg "$YELLOW" "Would you like to create it? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            create_venv "$venv_name"
        else
            print_msg "$RED" "Cannot proceed without venv. Exiting."
            exit 1
        fi
    else
        print_msg "$GREEN" "✓ Found venv: $venv_path"
    fi
}

# Create virtual environment
create_venv() {
    local venv_name=$1
    local venv_path="$VENV_BASE/$venv_name"
    local config_file="$DEADLYMUSUBI_ROOT/venv_configs/${CONFIG_NAME}.txt"
    
    if [ ! -f "$config_file" ]; then
        print_msg "$RED" "Configuration file not found: $config_file"
        exit 1
    fi
    
    print_msg "$BLUE" "Creating virtual environment: $venv_name"
    
    # Create venv
    python3 -m venv "$venv_path"
    
    # Activate and install
    source "$venv_path/bin/activate"
    
    print_msg "$BLUE" "Installing packages from $CONFIG_NAME..."
    pip install --upgrade pip
    pip install -r "$config_file"
    
    print_msg "$GREEN" "✓ Virtual environment created successfully"
}

# System check
system_check() {
    print_msg "$BLUE" "Performing system checks..."
    
    # Check GPU
    if ! command -v nvidia-smi &> /dev/null; then
        print_msg "$RED" "✗ nvidia-smi not found. NVIDIA drivers may not be installed."
        exit 1
    fi
    
    # Get GPU info
    gpu_info=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -n1)
    print_msg "$GREEN" "✓ GPU: $gpu_info"
    
    # Check VRAM
    vram_free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -n1)
    if [ "$vram_free" -lt 10000 ]; then
        print_msg "$YELLOW" "⚠ Warning: Low free VRAM ($vram_free MB). Consider closing other GPU applications."
    fi
    
    # Check CUDA
    if command -v nvcc &> /dev/null; then
        cuda_version=$(nvcc --version | grep "release" | sed 's/.*release //' | sed 's/,.*//')
        print_msg "$GREEN" "✓ CUDA: $cuda_version"
    else
        print_msg "$YELLOW" "⚠ CUDA toolkit not found (may not be required)"
    fi
}

# Launch training
launch_training() {
    local venv_name="deadly_musubi_${CONFIG_NAME}"
    local venv_path="$VENV_BASE/$venv_name"
    
    if [ "$DRY_RUN" = true ]; then
        print_msg "$YELLOW" "DRY RUN - Would execute:"
        echo "  Venv: $venv_path"
        echo "  Config: $CONFIG_NAME"
        echo "  Project: $PROJECT_NAME"
        return
    fi
    
    # Activate venv
    print_msg "$BLUE" "Activating venv: $venv_name"
    source "$venv_path/bin/activate"
    
    # Verify PyTorch
    print_msg "$BLUE" "Verifying PyTorch installation..."
    python3 << EOF
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA Version: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
EOF
    
    print_msg "$GREEN" "✓ Environment ready"
    print_msg "$BLUE" "To start training, activate the venv and run your training script:"
    echo ""
    echo "  source $venv_path/bin/activate"
    echo "  cd /path/to/musubi-tuner"
    echo "  # Run your training command"
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_NAME="$2"
            shift 2
            ;;
        -p|--project)
            PROJECT_NAME="$2"
            shift 2
            ;;
        -v|--venv-path)
            VENV_BASE="$2"
            shift 2
            ;;
        -l|--list)
            list_configs
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_msg "$RED" "Unknown option: $1"
            usage
            ;;
    esac
done

# Main execution
main() {
    print_msg "$GREEN" "╔════════════════════════════════════════╗"
    print_msg "$GREEN" "║      DeadlyMusubi Launcher v1.0        ║"
    print_msg "$GREEN" "╚════════════════════════════════════════╝"
    echo ""
    
    system_check
    echo ""
    
    venv_name="deadly_musubi_${CONFIG_NAME}"
    check_venv "$venv_name"
    echo ""
    
    launch_training
}

main
