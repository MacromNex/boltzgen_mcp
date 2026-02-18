#!/bin/bash
# BoltzGen MCP Quick Setup Script
# This script sets up the conda environment and downloads necessary dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="${SCRIPT_DIR}/env"
PYTHON_VERSION="3.12"
REPO_DIR="${SCRIPT_DIR}/repo"
BOLTZGEN_REPO="https://github.com/HannesStark/boltzgen.git"

# Print banner
echo -e "${BLUE}"
echo "=============================================="
echo "       BoltzGen MCP Quick Setup Script       "
echo "=============================================="
echo -e "${NC}"

# Function to print status messages
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check for conda/mamba
check_conda() {
    if command -v mamba &> /dev/null; then
        CONDA_CMD="mamba"
        info "Using mamba (faster package resolution)"
    elif command -v conda &> /dev/null; then
        CONDA_CMD="conda"
        info "Using conda"
    else
        error "Neither conda nor mamba found. Please install Miniconda or Mambaforge first."
        echo "  Install Miniconda: https://docs.conda.io/en/latest/miniconda.html"
        echo "  Install Mambaforge: https://github.com/conda-forge/miniforge"
        exit 1
    fi
}

# Parse command line arguments
SKIP_ENV=false
SKIP_REPO=false
SKIP_MODELS=false
DOWNLOAD_MODELS=false
HELP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-env)
            SKIP_ENV=true
            shift
            ;;
        --skip-repo)
            SKIP_REPO=true
            shift
            ;;
        --skip-models)
            SKIP_MODELS=true
            shift
            ;;
        --download-models)
            DOWNLOAD_MODELS=true
            shift
            ;;
        -h|--help)
            HELP=true
            shift
            ;;
        *)
            warn "Unknown option: $1"
            shift
            ;;
    esac
done

# Show help
if [ "$HELP" = true ]; then
    echo "Usage: ./quick_setup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-env         Skip conda environment creation"
    echo "  --skip-repo        Skip cloning the original BoltzGen repository"
    echo "  --skip-models      Skip model download prompt"
    echo "  --download-models  Automatically download models (~6GB)"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Example:"
    echo "  ./quick_setup.sh                    # Full setup with prompts"
    echo "  ./quick_setup.sh --download-models  # Full setup with automatic model download"
    echo "  ./quick_setup.sh --skip-repo        # Setup without cloning original repo"
    exit 0
fi

# Check prerequisites
info "Checking prerequisites..."
check_conda

# Check for git
if ! command -v git &> /dev/null; then
    error "git is not installed. Please install git first."
    exit 1
fi

success "Prerequisites check passed"

# Step 1: Create conda environment
echo ""
echo -e "${BLUE}Step 1: Setting up conda environment${NC}"
echo "--------------------------------------"

# Fast path: use pre-packaged conda env from GitHub Releases
PACKED_ENV_URL="${PACKED_ENV_URL:-}"
PACKED_ENV_TAG="${PACKED_ENV_TAG:-envs-v1}"
PACKED_ENV_BASE="https://github.com/charlesxu90/ProteinMCP/releases/download/${PACKED_ENV_TAG}"

if [ "$SKIP_ENV" = true ]; then
    info "Skipping environment creation (--skip-env)"
elif [ -d "$ENV_DIR" ] && [ -f "$ENV_DIR/bin/python" ]; then
    info "Environment already exists at: $ENV_DIR"
elif [ "${USE_PACKED_ENVS:-}" = "1" ] || [ -n "$PACKED_ENV_URL" ]; then
    # Download and extract pre-packaged conda environment
    # Supports both single file and split archives (part-aa, part-ab, ...)
    mkdir -p "$ENV_DIR"
    PACKED_ENV_DOWNLOADED=false

    if [ -n "$PACKED_ENV_URL" ]; then
        # Direct URL provided
        info "Downloading pre-packaged environment from ${PACKED_ENV_URL}..."
        if wget -qO- "$PACKED_ENV_URL" | tar xzf - -C "$ENV_DIR"; then
            PACKED_ENV_DOWNLOADED=true
        fi
    else
        # Try single file first, then split parts
        SINGLE_URL="${PACKED_ENV_BASE}/boltzgen_mcp-env.tar.gz"
        info "Trying single archive from ${SINGLE_URL}..."
        if wget -qO- "$SINGLE_URL" 2>/dev/null | tar xzf - -C "$ENV_DIR" 2>/dev/null; then
            PACKED_ENV_DOWNLOADED=true
        else
            info "Single archive not found, trying split parts..."
            TMPDIR_PARTS=$(mktemp -d)
            PART_IDX=0
            for SUFFIX in aa ab ac ad ae af; do
                PART_URL="${PACKED_ENV_BASE}/boltzgen_mcp-env.tar.gz.part-${SUFFIX}"
                if wget -q -O "${TMPDIR_PARTS}/part-${SUFFIX}" "$PART_URL" 2>/dev/null; then
                    PART_IDX=$((PART_IDX + 1))
                else
                    break
                fi
            done
            if [ "$PART_IDX" -gt 0 ]; then
                info "Downloaded ${PART_IDX} parts, reassembling..."
                cat "${TMPDIR_PARTS}"/part-* | tar xzf - -C "$ENV_DIR"
                PACKED_ENV_DOWNLOADED=true
            fi
            rm -rf "$TMPDIR_PARTS"
        fi
    fi

    if [ "$PACKED_ENV_DOWNLOADED" = true ]; then
        source "$ENV_DIR/bin/activate"
        conda-unpack 2>/dev/null || true
        success "Pre-packaged environment ready"
        SKIP_ENV=true
    else
        warn "Failed to download pre-packaged env, falling back to conda create..."
        rm -rf "$ENV_DIR"
        info "Creating conda environment with Python ${PYTHON_VERSION}..."
        $CONDA_CMD create -p "$ENV_DIR" python=${PYTHON_VERSION} -y
    fi
else
    info "Creating conda environment with Python ${PYTHON_VERSION}..."
    $CONDA_CMD create -p "$ENV_DIR" python=${PYTHON_VERSION} -y
fi

# Step 2: Install dependencies
echo ""
echo -e "${BLUE}Step 2: Installing dependencies${NC}"
echo "--------------------------------"

if [ "$SKIP_ENV" = true ]; then
    info "Skipping dependency installation (--skip-env)"
else
    if [ -f "${SCRIPT_DIR}/requirements.txt" ]; then
        info "Installing from requirements.txt..."
        "${ENV_DIR}/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt"
    else
        info "Installing core MCP dependencies..."
        "${ENV_DIR}/bin/pip" install fastmcp==2.13.3 loguru==0.7.3
        info "Installing BoltzGen (this may take a few minutes)..."
        "${ENV_DIR}/bin/pip" install boltzgen
    fi

    info "Installing fastmcp..."
    "${ENV_DIR}/bin/pip" install --ignore-installed fastmcp

    success "Dependencies installed successfully"
fi

# Step 3: Clone original repository (optional, for reference)
echo ""
echo -e "${BLUE}Step 3: Cloning original BoltzGen repository${NC}"
echo "----------------------------------------------"

if [ "$SKIP_REPO" = true ]; then
    info "Skipping repository clone (--skip-repo)"
elif [ -d "$REPO_DIR/boltzgen" ]; then
    warn "BoltzGen repository already exists at: $REPO_DIR/boltzgen"
    read -p "Do you want to update it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Updating repository..."
        cd "$REPO_DIR/boltzgen" && git pull
        cd "$SCRIPT_DIR"
    fi
else
    info "Cloning BoltzGen repository for reference..."
    mkdir -p "$REPO_DIR"
    git clone "$BOLTZGEN_REPO" "$REPO_DIR/boltzgen"
    success "Repository cloned to: $REPO_DIR/boltzgen"
fi

# Step 4: Download model weights (optional)
echo ""
echo -e "${BLUE}Step 4: Model weights download${NC}"
echo "-------------------------------"

if [ "$SKIP_MODELS" = true ]; then
    info "Skipping model download (--skip-models)"
elif [ "$DOWNLOAD_MODELS" = true ]; then
    info "Downloading BoltzGen models (~6GB)..."
    info "Models will be saved to ~/.cache (or \$HF_HOME if set)"
    $CONDA_CMD run -p "$ENV_DIR" boltzgen download all
    success "Models downloaded successfully"
else
    echo ""
    echo "BoltzGen requires model weights (~6GB) to run."
    echo "Models can be downloaded now or will auto-download on first use."
    echo ""
    read -p "Download models now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Downloading BoltzGen models..."
        $CONDA_CMD run -p "$ENV_DIR" boltzgen download all
        success "Models downloaded successfully"
    else
        info "Models will be downloaded automatically on first use"
    fi
fi

# Step 5: Verify installation
echo ""
echo -e "${BLUE}Step 5: Verifying installation${NC}"
echo "-------------------------------"

info "Checking Python version..."
$CONDA_CMD run -p "$ENV_DIR" python --version

info "Checking BoltzGen installation..."
$CONDA_CMD run -p "$ENV_DIR" boltzgen --help > /dev/null 2>&1 && success "BoltzGen CLI available" || error "BoltzGen CLI not found"

info "Checking MCP server..."
$CONDA_CMD run -p "$ENV_DIR" python -c "from src.server import mcp; print('MCP server ready')" 2>/dev/null && success "MCP server ready" || warn "MCP server check failed (may need to cd to project directory)"

# Print summary
echo ""
echo -e "${GREEN}=============================================="
echo "           Setup Complete!"
echo "==============================================${NC}"
echo ""
echo "Environment location: $ENV_DIR"
echo "Original repo: $REPO_DIR/boltzgen"
echo ""
echo -e "${YELLOW}Quick Start:${NC}"
echo ""
echo "  # Activate environment"
echo "  $CONDA_CMD activate $ENV_DIR"
echo ""
echo "  # Run protein binder design (local)"
echo "  python scripts/protein_binder_design.py \\"
echo "    --input examples/data/1g13prot.yaml \\"
echo "    --output results/test \\"
echo "    --num_designs 5"
echo ""
echo "  # Start MCP server"
echo "  python src/server.py"
echo ""
echo "  # Or install for Claude Code"
echo "  claude mcp add boltzgen -- $ENV_DIR/bin/python $SCRIPT_DIR/src/server.py"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "  - README.md: Full documentation"
echo "  - reports/step3_environment.md: Environment details"
echo "  - repo/boltzgen/README.md: Original BoltzGen documentation"
echo ""
