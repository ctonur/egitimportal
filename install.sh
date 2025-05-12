#!/bin/bash

# Define colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print banner
echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}OpenShift CLI Lab Platform Installer${NC}"
echo -e "${GREEN}=================================${NC}"

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check Python version
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"
else
    echo -e "${RED}✗${NC} Python 3 not found. Please install Python 3.7 or higher."
    exit 1
fi

# Check CLI tools
declare -a CLI_TOOLS=("oc" "kubectl" "docker")
for tool in "${CLI_TOOLS[@]}"; do
    if command -v "$tool" &>/dev/null; then
        echo -e "${GREEN}✓${NC} $tool found"
    else
        echo -e "${YELLOW}⚠${NC} $tool not found. Some labs may not work without it."
    fi
done

# Set up environment
echo -e "\n${YELLOW}Setting up environment...${NC}"

# Setup virtual environment and install dependencies
echo -e "Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
    # Create virtual environment
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗${NC} Failed to create virtual environment"
        echo -e "Make sure python3-venv is installed: sudo apt install python3-venv"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${YELLOW}⚠${NC} Virtual environment already exists"
fi

# Activate virtual environment
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} Failed to activate virtual environment"
    exit 1
fi

# Install Python dependencies
echo -e "Installing Python dependencies..."
pip install -r backend/requirements.txt
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Python dependencies installed successfully"
else
    echo -e "${RED}✗${NC} Failed to install Python dependencies"
    deactivate
    exit 1
fi

# Make sure the backend/labs directory exists
mkdir -p backend/labs

# Ensure we have execute permissions
chmod +x backend/app.py

# Check if Flask server is already running
if pgrep -f "python3 backend/app.py" > /dev/null; then
    echo -e "${YELLOW}⚠${NC} Flask server is already running. Stopping it..."
    pkill -f "python3 backend/app.py"
    sleep 2
fi

# Start Flask server (using the virtual environment's Python)
echo -e "Starting Flask server on port 80 (requires sudo)..."
sudo nohup .venv/bin/python backend/app.py > backend/server.log 2>&1 &
SERVER_PID=$!

# Check if server started successfully
sleep 2
if ps -p $SERVER_PID > /dev/null; then
    echo -e "${GREEN}✓${NC} Flask server started successfully (PID: $SERVER_PID)"
    echo -e "Server log: $(pwd)/backend/server.log"
else
    echo -e "${RED}✗${NC} Failed to start Flask server"
    echo -e "Check logs for details: $(pwd)/backend/server.log"
    exit 1
fi

# Deactivate the virtual environment
deactivate

# Print access information
echo -e "\n${GREEN}=================================${NC}"
echo -e "${GREEN}Setup completed successfully${NC}"
echo -e "${GREEN}=================================${NC}"
echo -e "\nAccess the OpenShift CLI Lab Platform at: ${YELLOW}http://$(hostname -I | awk '{print $1}'):80${NC}"
echo -e "\nTo stop the server: ${YELLOW}sudo pkill -f \"python3 backend/app.py\"${NC}"