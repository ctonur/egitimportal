#!/bin/bash

# Create a virtual environment
echo "Creating Python virtual environment..."
python3 -m venv .venv

# Activate the virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install required packages from requirements.txt
if [ -f "backend/requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r backend/requirements.txt
else
    echo "No requirements.txt found in backend directory."
    echo "Installing basic dependencies..."
    pip install flask kubernetes openshift
fi

echo ""
echo "✅ Virtual environment setup complete!"
echo "To activate the virtual environment in the future, run:"
echo "    source .venv/bin/activate"
echo ""
echo "To deactivate when finished, simply run:"
echo "    deactivate"