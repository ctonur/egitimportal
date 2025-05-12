#!/bin/bash

# oc_workspace_init.sh
# Script to set up isolated OpenShift kubeconfig for each student session
# This ensures students don't share the same kubeconfig file

# Detect the current working directory
CURRENT_DIR=$(pwd)

# Check if we're in a session directory (workspace/namespace/<session-id>)
if [[ "$CURRENT_DIR" =~ workspace/namespace/([^/]+) ]]; then
    # Extract the session ID from the directory structure
    SESSION_ID=${BASH_REMATCH[1]}
    
    # Define the base path for kubeconfig
    KUBECONFIG_PATH="$CURRENT_DIR/.kube/config"
    
    # Create the kubeconfig directory if it doesn't exist
    if [ ! -d "$CURRENT_DIR/.kube" ]; then
        echo "Creating isolated kubeconfig workspace for session $SESSION_ID..."
        mkdir -p "$CURRENT_DIR/.kube"
        touch "$KUBECONFIG_PATH"
        echo "Workspace created at $KUBECONFIG_PATH"
    fi
    
    # Set the KUBECONFIG environment variable
    export KUBECONFIG="$KUBECONFIG_PATH"
    
    # Update the PATH to include the OpenShift client binary location if needed
    # Uncomment if your oc binary is in a non-standard location
    # export PATH="/usr/lib/oc:$PATH"
    
    # Display information
    echo "✅ Isolated kubeconfig is now active for this session:"
    echo "  → KUBECONFIG = $KUBECONFIG_PATH"
    echo "  → SESSION ID = $SESSION_ID"
    echo "  → Working Directory = $CURRENT_DIR"
    echo "You can now run 'oc login' safely in your isolated environment."
else
    echo "⚠️ Not in a valid session directory."
    echo "This script should be run from within a workspace/namespace/<session-id> directory."
    echo "Current directory: $CURRENT_DIR"
fi