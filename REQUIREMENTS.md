# REQUIREMENTS.md

## 1. Product Vision & Scope
**Name:** Claude Code Orchestrator (Internal Tool)
**Platform:** Windows Desktop (Local Environment Only)
**Purpose:** An autonomous, multi-agent orchestration desktop application built in Python/PyQt5. It manages queues of tasks, executing them sequentially via the `claude-code` CLI. It handles API rate limits (specifically the 5-hour rolling limit) through persistent, interval-based retries, and validates work autonomously using a secondary LLM verification step.

## 2. Technical Stack
*   **Language:** Python 3.x
*   **GUI Framework:** PyQt5
*   **Data Persistence:** Local JSON file (`queue_state.json`) for task queues, `.env` file for secrets.
*   **Process Management:** Python `subprocess.Popen` for headless CLI execution.
*   **Target CLI:** Anthropic's Claude Code (`claude`)

## 3. Architecture: Multi-Agent System
The application orchestrates tasks through three distinct internal sub-agents:

### 3.1. The Manager Agent
*   **Role:** The overarching loop controller and queue manager.
*   **Responsibilities:**
    *   Pulls the next available task from the queue.
    *   Appends specific "one-shot" instructions to the task prompt to ensure the Worker does not wait for human interaction.
    *   Spawns the Worker process.
    *   Polls the status of the active agents.
    *   Handles the timeout/retry interval logic (retrying every *n* minutes up to a high maximum to outlast 5-hour rate limit windows).

### 3.2. The Worker Agent
*   **Role:** The executor.
*   **Responsibilities:**
    *   Executes `claude-code` in headless mode using the `--dangerously-skip-permissions` flag.
    *   Clones the target repository (using host machine's existing Git Credentials).
    *   Creates and checks out a local feature branch: `feature/<summary>`.
    *   Attempts to complete the task based on the Manager's augmented prompt.
    *   Outputs standard execution logs to the shared terminal UI.

### 3.3. The Controller Agent
*   **Role:** The LLM-oriented Quality Assurance validator.
*   **Responsibilities:**
    *   Triggered when the Worker completes a run.
    *   Spawns a separate instance of `claude-code` pointing at the local workspace.
    *   Evaluates the changes made by the Worker against the original task requirements.
    *   **Feedback Loop:** If the Controller determines the task is incomplete or incorrect, it shifts the task state back to `In Progress`, triggering the Worker to immediately attempt fixes on the *existing* local branch. If validated, it approves the task to the Manager.

## 4. Task Management & State Machine
### 4.1. Task Definition
A task represents a unit of work and consists of:
*   `Task ID` (Auto-generated or Jira Key)
*   `Summary` (Used for branch naming and overview)
*   `Description` (The detailed prompt/requirements)
*   `Target Repository URL`

### 4.2. Input Methods
Tasks can be ingested via three methods:
1.  **Manual Entry:** Form inside the PyQt5 UI.
2.  **Bulk Import:** Loading from a local text/CSV file.
3.  **Jira Integration:** Fetching via Jira REST API using a Jira Personal Access Token (PAT). Maps Jira "Summary" to Task Summary, and Jira "Description" to Task Description.

### 4.3. State Machine
Tasks exist in one of the following states, visible in the UI queue:
*   `Backlog`: Waiting to be picked up by the Manager.
*   `In Progress`: Currently being executed by the Worker (or returned here by the Controller for immediate fixing).
*   `In Review`: Being evaluated by the Controller.
*   `Will Retry`: Hit a failure or rate limit. Waiting for the *n*-minute cooldown before the Manager retries.
*   `Done`: Controller validated the work. Branch remains local (no remote push).
*   `Failed`: Exceeded the absolute maximum retry limit (e.g., 50 retries).

### 4.4. The 5-Hour Limit Handling
*   The application does *not* parse error logs for specific 5-hour limit strings. 
*   Instead, any failure (timeout, crash, rate limit) transitions the task to `Will Retry`.
*   The Manager pauses for an *n*-minute interval, then retries.
*   **Max Retries:** Set exceptionally high (e.g., 50+) ensuring that continuous retries will naturally span across the 5-hour cooldown window until the API limit refreshes and the task succeeds.

## 5. User Interface (PyQt5)
The desktop application must include three primary UI panels:

### 5.1. Queue Dashboard (Left/Top Panel)
*   A visual list/table of all tasks loaded from the JSON state file.
*   Displays Task ID, Summary, and Current State.
*   Controls to Add, Edit, Delete, or prioritize tasks.

### 5.2. Live Terminal Output (Right/Bottom Panel)
*   A read-only console window displaying `stdout` and `stderr` from the `Popen` processes.
*   **Color-Coding:** Output must be strictly color-coded by the agent generating it to maintain readability:
    *   *Manager Output:* Blue
    *   *Worker Output:* Green
    *   *Controller Output:* Magenta
    *   *System/Errors:* Red

### 5.3. Parameters & Environment Menu (Modal/Tab)
*   A dedicated settings menu to manage system environment variables.
*   **Pre-loaded Variables:** Must include known Claude Code variables (e.g., `CLAUDE_CODE_MAX_CONTEXT_TOKENS`) with UI tooltips/explanations of what they do.
*   **Custom Variables:** Ability to add, edit, and delete new key-value pairs.
*   **App Settings:** Configurable retry interval (*n* minutes) and absolute max retry count.

## 6. Data & Security Configurations
*   **Local State:** All queue data and parameters are saved to a local JSON file to ensure state persists if the application is closed or the machine reboots.
*   **Secrets:** Jira PAT and any explicitly required API keys are stored securely in a local `.env` file parsed at runtime.
*   **Git Auth:** No custom git credential handling is required; the app relies entirely on the host Windows machine's native Git Credential Manager.
