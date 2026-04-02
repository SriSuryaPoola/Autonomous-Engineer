"""
Global settings and configuration for the Autonomous Engineering Team.
"""

# ─── Execution Limits ─────────────────────────────────────────────────────────
MAX_RETRIES = 3                 # Max retry attempts per task in self-improvement loop
QUALITY_THRESHOLD = 0.7         # Minimum quality score (0.0–1.0) to accept output
PARALLEL_WORKERS = 4            # Max concurrent worker executions
CLAUDE_FLOW_MAX_MICRO_TASKS = 10  # Max micro-tasks a Claude Flow phase can spawn

# ─── Cost Control ─────────────────────────────────────────────────────────────
TOKEN_BUDGET_PER_TASK = 100000  # Max token budget per task
EARLY_STOPPING_ROUNDS = 2       # Stop early if no improvement over X rounds
TIMEOUT_PER_TOOL = 60           # Max execution seconds before killing tool process
MAX_RETRIES_PER_WORKER = 3      # Worker-level tool retry tolerance

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"              # DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_FORMAT = "[%(asctime)s] [%(name)-20s] [%(levelname)-8s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ─── Worker Role Definitions ─────────────────────────────────────────────────
WORKER_ROLES = {
    "SOFTWARE_DEVELOPER": {
        "description": "Designs architecture, writes production code, builds frameworks.",
        "capabilities": [
            "code_architecture",
            "implementation",
            "framework_setup",
            "refactoring",
            "documentation",
        ],
        "priority": 1,
    },
    "QA_ENGINEER": {
        "description": "Designs test cases, writes automation scripts, analyzes coverage.",
        "capabilities": [
            "test_design",
            "test_automation",
            "coverage_analysis",
            "bug_reporting",
            "regression_testing",
        ],
        "priority": 2,
    },
    "CODE_REVIEWER": {
        "description": "Reviews code quality, enforces best practices, security audits.",
        "capabilities": [
            "code_review",
            "best_practices",
            "security_audit",
            "performance_review",
            "style_enforcement",
        ],
        "priority": 3,
    },
    "DEVOPS_ENGINEER": {
        "description": "Creates CI/CD pipelines, deployment configs, infrastructure setup.",
        "capabilities": [
            "ci_cd_pipeline",
            "deployment",
            "containerization",
            "monitoring",
            "infrastructure",
        ],
        "priority": 4,
    },
    "RESEARCH_ANALYST": {
        "description": "Conducts research, feasibility studies, data analysis.",
        "capabilities": [
            "research",
            "data_analysis",
            "feasibility_study",
            "technology_evaluation",
            "reporting",
        ],
        "priority": 5,
    },
}

# ─── Claude Flow Phase Configuration ─────────────────────────────────────────
CLAUDE_FLOW_PHASES = [
    {
        "name": "understand",
        "description": "Parse the task and extract requirements",
        "sub_agent": "Researcher",
        "max_duration_seconds": 30,
    },
    {
        "name": "plan",
        "description": "Break task into ordered micro-tasks",
        "sub_agent": "Planner",
        "max_duration_seconds": 30,
    },
    {
        "name": "execute",
        "description": "Run each micro-task step by step",
        "sub_agent": "Coder",
        "max_duration_seconds": 120,
    },
    {
        "name": "validate",
        "description": "Self-check the output quality",
        "sub_agent": "Tester",
        "max_duration_seconds": 30,
    },
    {
        "name": "refine",
        "description": "Iterate and improve if validation fails",
        "sub_agent": "Validator",
        "max_duration_seconds": 60,
    },
]

# ─── Task Categories (for TaskAssigner routing) ──────────────────────────────
TASK_CATEGORY_TO_ROLE = {
    "code": "SOFTWARE_DEVELOPER",
    "implementation": "SOFTWARE_DEVELOPER",
    "framework": "SOFTWARE_DEVELOPER",
    "architecture": "SOFTWARE_DEVELOPER",
    "refactor": "SOFTWARE_DEVELOPER",
    "test": "QA_ENGINEER",
    "qa": "QA_ENGINEER",
    "automation": "QA_ENGINEER",
    "coverage": "QA_ENGINEER",
    "review": "CODE_REVIEWER",
    "audit": "CODE_REVIEWER",
    "security": "CODE_REVIEWER",
    "quality": "CODE_REVIEWER",
    "deploy": "DEVOPS_ENGINEER",
    "ci": "DEVOPS_ENGINEER",
    "cd": "DEVOPS_ENGINEER",
    "pipeline": "DEVOPS_ENGINEER",
    "infrastructure": "DEVOPS_ENGINEER",
    "docker": "DEVOPS_ENGINEER",
    "research": "RESEARCH_ANALYST",
    "analysis": "RESEARCH_ANALYST",
    "feasibility": "RESEARCH_ANALYST",
    "data": "RESEARCH_ANALYST",
    "evaluate": "RESEARCH_ANALYST",
}

# ─── Quality Scoring Weights ─────────────────────────────────────────────────
QUALITY_WEIGHTS = {
    "completeness": 0.30,
    "correctness": 0.30,
    "clarity": 0.15,
    "modularity": 0.15,
    "documentation": 0.10,
}
