document.addEventListener('DOMContentLoaded', () => {
    // State
    let currentQuestionId = null;
    let currentQuestion = null;
    let currentStepIndex = 0;
    let completedSteps = [];
    let namespace = '';
    let sessionId = '';

    // DOM Elements - Question List View
    const questionsListView = document.getElementById('questions-list-view');
    const questionsContainer = document.getElementById('questions-container');
    
    // DOM Elements - Question View
    const questionView = document.getElementById('question-view');
    const backToListBtn = document.getElementById('backToListBtn');
    const questionTitle = document.getElementById('question-title');
    const questionDescription = document.getElementById('question-description');
    const stepIndicator = document.getElementById('step-indicator');
    const namespaceSection = document.getElementById('namespace-section');
    const namespaceInput = document.getElementById('namespace-input');
    const createNamespaceBtn = document.getElementById('create-namespace-btn');
    const namespaceStatus = document.getElementById('namespace-status');
    const stepContent = document.getElementById('step-content');
    const prevStepBtn = document.getElementById('prevStepBtn');
    const checkBtn = document.getElementById('checkBtn');
    const nextStepBtn = document.getElementById('nextStepBtn');
    const resultDisplay = document.getElementById('result');
    
    // DOM Elements - Terminal
    const terminalOutput = document.getElementById('terminal-output');
    const terminalCommand = document.getElementById('terminal-command');

    // Initialize
    loadQuestions();
    setupTerminal();

    // Event listeners
    backToListBtn.addEventListener('click', (e) => {
        e.preventDefault();
        showQuestionListView();
    });
    
    createNamespaceBtn.addEventListener('click', createNamespace);
    checkBtn.addEventListener('click', validateCurrentStep);
    prevStepBtn.addEventListener('click', goToPreviousStep);
    nextStepBtn.addEventListener('click', goToNextStep);
    
    // Functions
    
    // Setup terminal functionality
    function setupTerminal() {
        terminalCommand.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter') {
                const command = terminalCommand.value.trim();
                if (command) {
                    // Clear the input field
                    terminalCommand.value = '';
                    
                    // Add command to terminal output
                    appendToTerminal(`$ ${command}`, 'command');
                    
                    // Execute command
                    await executeCommand(command);
                }
            }
        });
        
        // Add initial welcome message
        appendToTerminal('Terminal ready. Type commands to interact with the system.', 'system');
    }
    
    // Append text to terminal output
    function appendToTerminal(text, type = 'output') {
        if (type === 'output' && text.includes('\n')) {
            // Handle multi-line output by splitting into separate elements
            const lines = text.split('\n');
            for (const line of lines) {
                if (line.trim() !== '') {  // Skip empty lines
                    const lineElement = document.createElement('div');
                    lineElement.classList.add(type);
                    lineElement.textContent = line;
                    terminalOutput.appendChild(lineElement);
                }
            }
        } else {
            // Handle single-line output or special types (command, system, etc.)
            const line = document.createElement('div');
            line.classList.add(type);
            line.textContent = text;
            terminalOutput.appendChild(line);
        }
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
    
    // Execute command in terminal
    async function executeCommand(command) {
        try {
            // If we have an active namespace/session, pass it along
            const payload = { command };
            if (sessionId) {
                payload.sessionId = sessionId;
            }
            if (namespace) {
                payload.namespace = namespace;
            }
            
            const response = await fetch('/api/terminal/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                if (result.output) {
                    appendToTerminal(result.output);
                }
            } else {
                appendToTerminal(`Error: ${result.error || 'Failed to execute command'}`, 'error');
            }
        } catch (error) {
            console.error('Error executing command:', error);
            appendToTerminal(`Error: ${error.message || 'Connection error'}`, 'error');
        }
    }
    
    // Load all available questions
    async function loadQuestions() {
        try {
            const response = await fetch('/api/questions');
            if (!response.ok) {
                throw new Error(`Failed to load questions: ${response.statusText}`);
            }
            
            const questions = await response.json();
            renderQuestionsList(questions);
        } catch (error) {
            console.error('Error loading questions:', error);
            questionsContainer.innerHTML = `<div class="error">Error loading questions: ${error.message}</div>`;
        }
    }
    
    // Render the list of questions
    function renderQuestionsList(questions) {
        if (questions.length === 0) {
            questionsContainer.innerHTML = `
                <div class="info">
                    No questions available. Please visit the admin panel to create questions.
                </div>
            `;
            return;
        }
        
        questionsContainer.innerHTML = '';
        questions.forEach(question => {
            const questionCard = document.createElement('div');
            questionCard.className = 'question-card';
            questionCard.innerHTML = `
                <h3>${question.title || question.id}</h3>
                <p>${question.description || 'No description available.'}</p>
            `;
            questionCard.addEventListener('click', () => loadQuestion(question.id));
            questionsContainer.appendChild(questionCard);
        });
    }
    
    // Load a specific question
    async function loadQuestion(questionId) {
        try {
            const response = await fetch(`/api/questions/${questionId}`);
            if (!response.ok) {
                throw new Error(`Failed to load question: ${response.statusText}`);
            }
            
            currentQuestionId = questionId;
            currentQuestion = await response.json();
            
            // Reset state
            currentStepIndex = 0;
            completedSteps = [];
            
            // Create a new session for this question
            await createQuestionSession(questionId);
            
            // Show question view
            displayQuestion();
            showQuestionView();
        } catch (error) {
            console.error('Error loading question:', error);
            alert(`Error loading question: ${error.message}`);
        }
    }
    
    // Create a new session for a question
    async function createQuestionSession(questionId) {
        try {
            const response = await fetch('/api/session/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ questionId })
            });
            
            if (!response.ok) {
                throw new Error('Failed to create session');
            }
            
            const data = await response.json();
            sessionId = data.sessionId;
            
            // Clear terminal and add session info
            terminalOutput.innerHTML = '';
            appendToTerminal(`Session started for question: ${currentQuestion.title}`, 'system');
            appendToTerminal(`Working directory: workspace/namespace/${sessionId}`, 'system');
            appendToTerminal('Type commands to interact with your environment', 'system');
            
            // Execute the oc_workspace_init.sh script to set up isolated kubeconfig
            appendToTerminal('Setting up isolated OpenShift environment...', 'system');
            await executeCommand('source /home/osandikci/workspace/opens/scripts/oc_workspace_init.sh');
            appendToTerminal('Environment setup complete. You can now use the OpenShift CLI with an isolated configuration.', 'system');
            
            return true;
        } catch (error) {
            console.error('Error creating session:', error);
            appendToTerminal(`Error creating session: ${error.message}`, 'error');
            return false;
        }
    }
    
    // Display the current question
    function displayQuestion() {
        // Set title and description
        questionTitle.textContent = currentQuestion.title || currentQuestion.id;
        questionDescription.textContent = currentQuestion.description || '';
        
        // Setup step indicator
        setupStepIndicator();
        
        // Show the first step
        showCurrentStep();
    }
    
    // Setup step indicator dots
    function setupStepIndicator() {
        stepIndicator.innerHTML = '';
        
        if (currentQuestion && currentQuestion.steps) {
            currentQuestion.steps.forEach((step, index) => {
                const dot = document.createElement('div');
                dot.className = 'step-dot';
                if (index === currentStepIndex) {
                    dot.classList.add('active');
                } else if (completedSteps.includes(index)) {
                    dot.classList.add('completed');
                }
                dot.addEventListener('click', () => {
                    currentStepIndex = index;
                    showCurrentStep();
                });
                stepIndicator.appendChild(dot);
            });
        }
    }
    
    // Show current step content
    function showCurrentStep() {
        if (!currentQuestion || !currentQuestion.steps || currentQuestion.steps.length === 0) {
            stepContent.innerHTML = '<div class="error">No steps available</div>';
            return;
        }
        
        const step = currentQuestion.steps[currentStepIndex];
        
        // Update step indicator
        updateStepIndicator();
        
        // Display step content
        stepContent.innerHTML = step.content || 'No content for this step';
        
        // Add syntax highlighting and copy buttons to code blocks
        highlightCodeBlocks();
        
        // Update navigation buttons
        updateNavButtons();
        
        // Show/hide namespace section only for the first step
        namespaceSection.classList.toggle('hidden', currentStepIndex !== 0);
        
        // Clear result display
        clearResultDisplay();
    }
    
    // Update the step indicator dots
    function updateStepIndicator() {
        const dots = stepIndicator.querySelectorAll('.step-dot');
        dots.forEach((dot, index) => {
            dot.classList.toggle('active', index === currentStepIndex);
            dot.classList.toggle('completed', completedSteps.includes(index));
        });
    }
    
    // Update navigation buttons
    function updateNavButtons() {
        prevStepBtn.disabled = currentStepIndex === 0;
        nextStepBtn.disabled = currentStepIndex >= currentQuestion.steps.length - 1;
        
        prevStepBtn.classList.toggle('btn-disabled', prevStepBtn.disabled);
        nextStepBtn.classList.toggle('btn-disabled', nextStepBtn.disabled);
    }
    
    // Go to previous step
    function goToPreviousStep() {
        if (currentStepIndex > 0) {
            currentStepIndex--;
            showCurrentStep();
        }
    }
    
    // Go to next step
    function goToNextStep() {
        if (currentStepIndex < currentQuestion.steps.length - 1) {
            currentStepIndex++;
            showCurrentStep();
        }
    }
    
    // Create namespace for user
    async function createNamespace() {
        namespace = namespaceInput.value.trim();
        
        if (!namespace) {
            namespaceStatus.innerHTML = '<div class="error">Please enter a namespace name</div>';
            return;
        }
        
        try {
            createNamespaceBtn.disabled = true;
            namespaceStatus.innerHTML = '<div class="info">Checking namespace...</div>';
            
            // Instead of creating the namespace on the server, we'll check if the student has created it via CLI
            // Execute 'oc project -q' to get the current project
            const payload = { 
                command: 'oc project -q',
                sessionId
            };
            
            const response = await fetch('/api/terminal/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            // Check if the current project matches what the student entered
            if (response.ok && result.output && result.output.trim() === namespace.trim()) {
                namespaceStatus.innerHTML = `<div class="success">✅ Namespace "${namespace}" verified successfully!</div>`;
                namespaceSection.classList.add('completed-section');
                
                // Show success in terminal
                appendToTerminal(`Namespace verified: ${namespace}`, 'system');
            } else {
                // The project doesn't match or hasn't been created yet
                namespaceStatus.innerHTML = `<div class="error">❌ Namespace "${namespace}" not found or not set as current project.</div>`;
                appendToTerminal(`Please create your namespace using: oc new-project ${namespace}`, 'system');
                appendToTerminal(`Then verify with: oc project -q`, 'system');
            }
        } catch (error) {
            console.error('Error verifying namespace:', error);
            namespaceStatus.innerHTML = `<div class="error">❌ Error verifying namespace: ${error.message}</div>`;
        } finally {
            createNamespaceBtn.disabled = false;
        }
    }
    
    // Validate current step
    async function validateCurrentStep() {
        if (!currentQuestion || !currentQuestion.steps) return;
        
        const stepNumber = (currentStepIndex + 1).toString();
        
        checkBtn.disabled = true;
        showResultDisplay('Checking...', '');
        
        try {
            const response = await fetch('/api/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question_id: currentQuestionId,
                    step: stepNumber,
                    namespace,
                    sessionId
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                if (data.passed) {
                    showResultDisplay(`✅ Passed\n\n${data.output}`, 'success');
                    
                    // Mark step as completed
                    if (!completedSteps.includes(currentStepIndex)) {
                        completedSteps.push(currentStepIndex);
                        updateStepIndicator();
                    }
                    
                    // Auto-advance to next step after delay
                    if (currentStepIndex < currentQuestion.steps.length - 1) {
                        setTimeout(() => {
                            goToNextStep();
                        }, 1500);
                    }
                } else {
                    showResultDisplay(`❌ Failed\n\n${data.output}`, 'error');
                }
            } else {
                showResultDisplay(`❌ Error\n\n${data.error || 'Unknown error occurred'}`, 'error');
            }
        } catch (error) {
            console.error('Error validating step:', error);
            showResultDisplay(`❌ Error\n\n${error.message || 'Connection error'}`, 'error');
        } finally {
            checkBtn.disabled = false;
        }
    }
    
    // Display result message
    function showResultDisplay(message, className = '') {
        resultDisplay.textContent = message;
        resultDisplay.className = className;
        resultDisplay.classList.remove('hidden');
    }
    
    // Clear the result display
    function clearResultDisplay() {
        resultDisplay.textContent = '';
        resultDisplay.className = 'hidden';
    }
    
    // Toggle between question list and question view
    function showQuestionListView() {
        questionsListView.classList.remove('hidden');
        questionView.classList.add('hidden');
        
        // Clear current question
        currentQuestionId = null;
        
        // End session if active
        if (sessionId) {
            endSession();
        }
    }
    
    function showQuestionView() {
        questionsListView.classList.add('hidden');
        questionView.classList.remove('hidden');
    }
    
    // End the current session
    async function endSession() {
        if (!sessionId) return;
        
        try {
            await fetch('/api/session/end', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ sessionId })
            });
            
            sessionId = '';
            appendToTerminal('Session ended', 'system');
        } catch (error) {
            console.error('Error ending session:', error);
        }
    }
    
    // Format code blocks with syntax highlighting and copy buttons
    function highlightCodeBlocks() {
        const codeBlocks = document.querySelectorAll('pre code');
        codeBlocks.forEach(block => {
            // Add copy button
            const pre = block.parentElement;
            if (!pre.querySelector('.copy-button')) {
                const copyButton = document.createElement('button');
                copyButton.className = 'copy-button';
                copyButton.textContent = 'Copy';
                copyButton.addEventListener('click', () => {
                    navigator.clipboard.writeText(block.textContent)
                        .then(() => {
                            copyButton.textContent = 'Copied!';
                            setTimeout(() => {
                                copyButton.textContent = 'Copy';
                            }, 2000);
                        })
                        .catch(err => console.error('Could not copy: ', err));
                });
                pre.appendChild(copyButton);
            }
        });
    }
});