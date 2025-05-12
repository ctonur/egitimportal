#!/usr/bin/env python3
import os
import json
import uuid
import shutil
import subprocess
import threading
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# Root directory for the project
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')
LAB_DIR = os.path.join(os.path.dirname(__file__), 'labs')
QUESTIONS_DIR = os.path.join(os.path.dirname(__file__), 'questions')
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, 'workspace')

# Dictionary to keep track of active sessions and their workspaces
active_sessions = {}

# Setup workspaces directory
os.makedirs(os.path.join(WORKSPACE_DIR, 'namespace'), exist_ok=True)

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory(FRONTEND_DIR, 'admin.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return "File not found", 404

@app.route('/labs/<lab_name>/<path:path>')
def serve_lab_content(lab_name, path):
    lab_path = os.path.join(LAB_DIR, lab_name)
    if os.path.exists(os.path.join(lab_path, path)):
        return send_from_directory(lab_path, path)
    return "Lab content not found", 404

@app.route('/questions/<question_id>/<path:path>')
def serve_question_file(question_id, path):
    question_path = os.path.join(QUESTIONS_DIR, question_id)
    if os.path.exists(os.path.join(question_path, path)):
        return send_from_directory(question_path, path)
    return "Question resource not found", 404

@app.route('/api/questions')
def get_questions():
    try:
        questions = []
        # Check if questions directory exists
        if not os.path.exists(QUESTIONS_DIR):
            return jsonify({"error": "Questions directory not found"}), 404
            
        # List all question directories
        for question_id in os.listdir(QUESTIONS_DIR):
            question_dir = os.path.join(QUESTIONS_DIR, question_id)
            if os.path.isdir(question_dir):
                # Load metadata if exists
                metadata_path = os.path.join(question_dir, 'metadata.json')
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        questions.append({
                            'id': question_id,
                            'title': metadata.get('title', question_id),
                            'description': metadata.get('description', '')
                        })
                else:
                    # Add question without metadata
                    questions.append({
                        'id': question_id,
                        'title': question_id,
                        'description': ''
                    })
                    
        return jsonify(questions)
    except Exception as e:
        return jsonify({"error": f"Failed to load questions: {str(e)}"}), 500

@app.route('/api/questions/<question_id>')
def get_question(question_id):
    question_dir = os.path.join(QUESTIONS_DIR, question_id)
    
    if not os.path.exists(question_dir):
        return jsonify({"error": "Question not found"}), 404
    
    try:
        # Load metadata
        metadata_path = os.path.join(question_dir, 'metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {'title': question_id, 'description': ''}
        
        # Load steps
        steps = []
        steps_dir = os.path.join(question_dir, 'steps')
        if os.path.exists(steps_dir):
            step_files = sorted([f for f in os.listdir(steps_dir) if f.endswith('.md')], 
                               key=lambda x: int(x.split('.')[0]))
            
            for step_file in step_files:
                with open(os.path.join(steps_dir, step_file), 'r') as f:
                    step_content = f.read()
                    step_number = step_file.split('.')[0]
                    steps.append({
                        'id': step_number,
                        'content': step_content
                    })
        
        # Combine data
        question_data = {
            'id': question_id,
            'title': metadata.get('title', question_id),
            'description': metadata.get('description', ''),
            'steps': steps
        }
        
        return jsonify(question_data)
    except Exception as e:
        return jsonify({"error": f"Error loading question: {str(e)}"}), 500

@app.route('/api/validate', methods=['POST'])
def validate():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    lab = data.get('lab')
    question_id = data.get('question_id')
    step = str(data.get('step'))
    
    # Check if this is a lab validation or a question validation
    if lab:
        return validate_lab(lab, step)
    elif question_id:
        return validate_question(question_id, step)
    else:
        return jsonify({"error": "Missing lab or question_id parameter"}), 400

def validate_lab(lab, step):
    if not lab or step is None:
        return jsonify({"error": "Missing lab or step parameter"}), 400
    
    # Load the validation commands
    try:
        validate_path = os.path.join(LAB_DIR, lab, 'validate.json')
        with open(validate_path, 'r') as f:
            validation_commands = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": f"Lab '{lab}' not found"}), 404
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid validation file format"}), 500
    
    # Get the validation command for this step
    command = validation_commands.get(step)
    if not command:
        return jsonify({"error": f"Step {step} not found for lab '{lab}'"}), 404
    
    # Run the command
    return run_validation_command(command)

def validate_question(question_id, step):
    if not question_id or step is None:
        return jsonify({"error": "Missing question_id or step parameter"}), 400
    
    # Load the validation commands
    try:
        validate_path = os.path.join(QUESTIONS_DIR, question_id, 'validation.json')
        with open(validate_path, 'r') as f:
            validation_commands = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": f"Question '{question_id}' validation not found"}), 404
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid validation file format"}), 500
    
    # Get the validation command for this step
    command = validation_commands.get(step)
    if not command:
        return jsonify({"error": f"Step {step} not found for question '{question_id}'"}), 404
    
    # Replace any environment variables
    namespace = request.json.get('namespace', '')
    if namespace:
        command = command.replace('${NAMESPACE}', namespace)
    
    # Run the command
    return run_validation_command(command)

def run_validation_command(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10  # Timeout after 10 seconds
        )
        
        passed = result.returncode == 0
        output = result.stdout.strip() if passed else result.stderr.strip()
        
        return jsonify({
            "passed": passed,
            "output": output or "Command executed successfully"
        })
    except subprocess.TimeoutExpired:
        return jsonify({
            "passed": False,
            "output": "Command timed out after 10 seconds"
        })
    except Exception as e:
        return jsonify({
            "passed": False,
            "output": f"Error executing command: {str(e)}"
        }), 500

@app.route('/api/create-namespace', methods=['POST'])
def create_namespace():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    namespace = data.get('namespace')
    if not namespace:
        return jsonify({"error": "No namespace provided"}), 400
    
    try:
        # Delete namespace if it exists
        subprocess.run(
            f"oc delete namespace {namespace} --ignore-not-found",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Create namespace
        result = subprocess.run(
            f"oc create namespace {namespace}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "message": f"Namespace '{namespace}' created successfully"
            })
        else:
            return jsonify({
                "success": False,
                "message": result.stderr.strip() or "Failed to create namespace"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/admin/questions', methods=['GET'])
def admin_get_questions():
    """Get all questions for admin panel"""
    return get_questions()

@app.route('/api/admin/questions', methods=['POST'])
def admin_create_question():
    """Create a new question"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    question_id = data.get('id')
    if not question_id:
        return jsonify({"error": "No question ID provided"}), 400
    
    # Validate question ID format
    if not question_id.replace('-', '').isalnum():
        return jsonify({"error": "Question ID must contain only letters, numbers, and hyphens"}), 400
    
    question_dir = os.path.join(QUESTIONS_DIR, question_id)
    if os.path.exists(question_dir):
        return jsonify({"error": f"Question '{question_id}' already exists"}), 409
    
    try:
        # Create question directory structure
        os.makedirs(question_dir, exist_ok=True)
        os.makedirs(os.path.join(question_dir, 'steps'), exist_ok=True)
        
        # Create metadata.json
        metadata = {
            'title': data.get('title', 'New Question'),
            'description': data.get('description', '')
        }
        with open(os.path.join(question_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create empty validation.json
        with open(os.path.join(question_dir, 'validation.json'), 'w') as f:
            json.dump({}, f, indent=2)
        
        # Create first step
        with open(os.path.join(question_dir, 'steps', '1.md'), 'w') as f:
            f.write("# Step 1: Create your namespace\n\n"
                   "Enter a name for your namespace in the field above and click \"Create Namespace\" button.\n\n"
                   "**Note:** If the namespace already exists, it will be deleted and recreated.\n\n"
                   "After you've created your namespace, click the \"Check\" button to verify and proceed to the next step.")
        
        return jsonify({"success": True, "id": question_id}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create question: {str(e)}"}), 500

@app.route('/api/admin/questions/<question_id>', methods=['GET'])
def admin_get_question(question_id):
    """Get a question for admin editing"""
    return get_question(question_id)

@app.route('/api/admin/questions/<question_id>', methods=['PUT'])
def admin_update_question(question_id):
    """Update a question"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    question_dir = os.path.join(QUESTIONS_DIR, question_id)
    if not os.path.exists(question_dir):
        return jsonify({"error": f"Question '{question_id}' not found"}), 404
    
    try:
        # Update metadata
        metadata = {
            'title': data.get('title', ''),
            'description': data.get('description', '')
        }
        with open(os.path.join(question_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Update steps
        steps_dir = os.path.join(question_dir, 'steps')
        os.makedirs(steps_dir, exist_ok=True)
        
        # Remove existing steps
        for file in os.listdir(steps_dir):
            if file.endswith('.md'):
                os.remove(os.path.join(steps_dir, file))
        
        # Add new steps
        steps = data.get('steps', [])
        for step in steps:
            step_id = step.get('id')
            content = step.get('content', '')
            with open(os.path.join(steps_dir, f"{step_id}.md"), 'w') as f:
                f.write(content)
        
        # Update validations
        validations = data.get('validations', {})
        with open(os.path.join(question_dir, 'validation.json'), 'w') as f:
            json.dump(validations, f, indent=2)
        
        return jsonify({"success": True, "id": question_id})
    except Exception as e:
        return jsonify({"error": f"Failed to update question: {str(e)}"}), 500

@app.route('/api/admin/questions/<question_id>', methods=['DELETE'])
def admin_delete_question(question_id):
    """Delete a question"""
    question_dir = os.path.join(QUESTIONS_DIR, question_id)
    if not os.path.exists(question_dir):
        return jsonify({"error": f"Question '{question_id}' not found"}), 404
    
    try:
        import shutil
        shutil.rmtree(question_dir)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Failed to delete question: {str(e)}"}), 500

@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new terminal session"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    namespace = data.get('namespace')
    if not namespace:
        return jsonify({"error": "No namespace provided"}), 400
    
    # Create a unique session ID
    session_id = str(uuid.uuid4())
    
    # Create session directory
    session_dir = os.path.join(WORKSPACE_DIR, 'namespace', namespace, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # Create a new terminal session
    try:
        process = subprocess.Popen(
            ['bash'],
            cwd=session_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Store the process and session info
        active_sessions[session_id] = {
            'process': process,
            'namespace': namespace,
            'workspace': session_dir
        }
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": f"Session '{session_id}' created successfully"
        }), 201
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a terminal session"""
    session_info = active_sessions.get(session_id)
    if not session_info:
        return jsonify({"error": f"Session '{session_id}' not found"}), 404
    
    try:
        # Terminate the process
        session_info['process'].terminate()
        
        # Wait for the process to terminate
        session_info['process'].wait(timeout=5)
    except Exception as e:
        return jsonify({"error": f"Failed to terminate session: {str(e)}"}), 500
    finally:
        # Remove the session from active sessions
        active_sessions.pop(session_id, None)
    
    return jsonify({"success": True, "message": f"Session '{session_id}' deleted successfully"})

@app.route('/api/sessions/<session_id>/execute', methods=['POST'])
def execute_command(session_id):
    """Execute a command in the terminal session"""
    session_info = active_sessions.get(session_id)
    if not session_info:
        return jsonify({"error": f"Session '{session_id}' not found"}), 404
    
    data = request.json
    command = data.get('command')
    if not command:
        return jsonify({"error": "No command provided"}), 400
    
    try:
        # Execute the command
        session_info['process'].stdin.write(command + '\n')
        session_info['process'].stdin.flush()
        
        return jsonify({"success": True, "message": f"Command executed: {command}"})
    except Exception as e:
        return jsonify({"error": f"Failed to execute command: {str(e)}"}), 500

@app.route('/api/sessions/<session_id>/output', methods=['GET'])
def get_session_output(session_id):
    """Get the output of the terminal session"""
    session_info = active_sessions.get(session_id)
    if not session_info:
        return jsonify({"error": f"Session '{session_id}' not found"}), 404
    
    try:
        # Read the output and error streams
        stdout = session_info['process'].stdout.readline()
        stderr = session_info['process'].stderr.readline()
        
        return jsonify({
            "success": True,
            "output": stdout.strip(),
            "error": stderr.strip()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get session output: {str(e)}"}), 500

@app.route('/api/session/create', methods=['POST'])
def session_create():
    """Create a new workspace session for a question"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    question_id = data.get('questionId')
    if not question_id:
        return jsonify({"error": "No question ID provided"}), 400
    
    # Create a unique session ID
    session_id = str(uuid.uuid4())[:8]  # Use shortened UUID for readability
    
    try:
        # Create session directory
        session_dir = os.path.join(WORKSPACE_DIR, 'namespace', session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Store session information
        active_sessions[session_id] = {
            'question_id': question_id,
            'workspace': session_dir,
            'namespace': None,
            'created_at': os.path.getctime(session_dir)
        }
        
        return jsonify({
            "success": True,
            "sessionId": session_id,
            "workspacePath": session_dir
        })
    except Exception as e:
        return jsonify({"error": f"Failed to create session: {str(e)}"}), 500

@app.route('/api/session/end', methods=['POST'])
def session_end():
    """End a workspace session"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    session_id = data.get('sessionId')
    if not session_id or session_id not in active_sessions:
        return jsonify({"error": "Invalid session ID"}), 404
    
    try:
        # Get session info
        session_info = active_sessions[session_id]
        workspace_dir = session_info.get('workspace')
        
        # Clean up session resources
        if workspace_dir and os.path.exists(workspace_dir):
            # Optional: You could delete the workspace or keep it for history
            # shutil.rmtree(workspace_dir)
            pass
        
        # Remove session from active sessions
        active_sessions.pop(session_id, None)
        
        return jsonify({
            "success": True,
            "message": f"Session {session_id} ended"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to end session: {str(e)}"}), 500

@app.route('/api/terminal/execute', methods=['POST'])
def terminal_execute():
    """Execute a command in the terminal"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    command = data.get('command')
    if not command:
        return jsonify({"error": "No command provided"}), 400
    
    session_id = data.get('sessionId')
    namespace = data.get('namespace')
    
    # If we have a session, use its workspace
    cwd = None
    env = os.environ.copy()
    
    if session_id and session_id in active_sessions:
        session_info = active_sessions[session_id]
        cwd = session_info.get('workspace')
        
        # Update namespace if provided
        if namespace and not session_info.get('namespace'):
            session_info['namespace'] = namespace
        
        # Use the session's namespace if available
        if session_info.get('namespace'):
            env['NAMESPACE'] = session_info['namespace']
    
    try:
        # Execute the command
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30  # Allow longer timeout for user commands
        )
        
        # Combine output and error
        output = result.stdout
        if result.stderr:
            if output:
                output += "\n" + result.stderr
            else:
                output = result.stderr
        
        return jsonify({
            "success": result.returncode == 0,
            "output": output,
            "returnCode": result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "output": "Command timed out after 30 seconds"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "output": f"Error executing command: {str(e)}"
        }), 500

if __name__ == '__main__':
    # Ensure questions directory exists
    os.makedirs(QUESTIONS_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=80, debug=False)