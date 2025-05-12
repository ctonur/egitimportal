# OpenShift CLI Lab Platform

An interactive web-based platform for learning OpenShift, Kubernetes, and Docker CLI commands through guided lab exercises.

## Overview

This platform provides a two-pane interface:
- **Left pane**: Step-by-step instructions with copy-pastable commands
- **Right pane**: A "Check" button that validates if the command was executed correctly

Students run commands in their own terminal (where they've already performed `oc login`), and the platform validates their work by running validation commands on the host.

## Prerequisites

- **Operating System**: Linux
- **CLI Tools**: `oc`, `kubectl`, and/or `docker` available in your `$PATH`
- **Python**: Version 3.7 or higher
- **Browser**: Any modern web browser

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/opens.git
   cd opens
   ```

2. Run the installer:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## How It Works

1. The platform serves step-by-step Markdown instructions from `/backend/labs/<lab-name>/steps.md`
2. Each lab has a corresponding `validate.json` file mapping step numbers to validation commands
3. When you click "Check", the server runs the validation command and returns pass/fail results
4. All commands run on the same host where the server is running, so the validation process uses your existing CLI configurations

## Adding a New Lab

1. Create a new folder under `backend/labs/` with your lab name (e.g., `backend/labs/deploy-application/`)

2. Create two files in the new folder:

   a. `steps.md` - Contains the lab instructions in Markdown format:
   ```markdown
   # Lab: Deploy an Application
   
   This lab will guide you through deploying an application on OpenShift.
   
   ## Step 1
   
   Create a new project:
   
   ```bash
   oc new-project myapp
   ```
   
   ## Step 2
   ...
   ```

   b. `validate.json` - Maps each step to a validation command:
   ```json
   {
     "1": "oc get project myapp",
     "2": "oc get deployment myapp -n myapp"
   }
   ```

3. Restart the server to pick up the new lab:
   ```bash
   pkill -f "python3 backend/app.py"
   ./install.sh
   ```

## Architecture

```
┌────────────┐           HTTP           ┌──────────────┐
│   Browser  │  ◀───────────────▶        │   Flask     │
│ (HTML+JS)  │                          │  API Server  │
└────────────┘                          └──────────────┘
     │                                         │
     │ — fetch /labs/ID/steps.md → Markdown    │
     │ — fetch /api/validate (POST JSON) → JSON│
     │                                         │
     │                                         ▼
     │                             Runs `subprocess.run(...)`
     │                             against oc/kubectl/docker
     │
     ▼
 Students run commands in their *own* local terminal
 (already `oc login`) so Flask simply shells out
 on the same host.
```

## Project Structure

```
cli-lab-platform/
│
├── backend/
│   ├── app.py              ← Flask application
│   ├── requirements.txt    ← Flask, etc.
│   └── labs/
│       └── creating-configmap/
│           ├── steps.md    ← Markdown with "## Step 1", "## Step 2"...  
│           └── validate.json ← { "1": "oc get cm …", "2": "oc describe cm …" }
│
├── frontend/
│   ├── index.html          ← two-pane layout skeleton  
│   ├── styles.css          ← grid/flex CSS for sidebar & content  
│   └── main.js             ← loads steps.md, renders sidebar, calls /api/validate
│
├── install.sh              ← installs Python deps, syncs labs, launches Flask  
└── README.md               ← quickstart, adding new labs
```

## Stopping the Server

To stop the server, run:

```bash
pkill -f "python3 backend/app.py"
```

## Troubleshooting

If you encounter issues:

1. Check the server logs: `cat backend/server.log`
2. Ensure you have the required CLI tools installed and in your PATH
3. Verify you have performed `oc login` in your terminal if using OpenShift labs