"""Comprehensive v2 Improvement Validation Suite"""
import sys, os
sys.path.insert(0, r'C:\Users\Pula Srisurya\Desktop\Autonomus engineer')
ROOT = r'C:\Users\Pula Srisurya\Desktop\Autonomus engineer'
p = f = 0

def chk(name, ok, detail=''):
    global p, f
    if ok: p += 1
    else: f += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))

def rd(path): return open(path, encoding='utf-8', errors='replace').read()
def exists(path): return os.path.exists(os.path.join(ROOT, path))
def isdir(path): return os.path.isdir(os.path.join(ROOT, path))

def section(t): print(f"\n=== {t} ===")

# ─── WAVE 1: P0 Quick Fixes ──────────────────────────────────────────────────
section("WAVE 1 — P0 QUICK FIXES")
chk('.env.example exists', exists('.env.example'))
try:
    env = rd(os.path.join(ROOT, '.env.example'))
    chk('.env.example has ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY' in env)
    chk('.env.example has LLM_PROVIDER', 'LLM_PROVIDER' in env)
    chk('.env.example has OLLAMA_HOST', 'OLLAMA_HOST' in env)
    chk('.env.example has DOCKER_SANDBOX', 'DOCKER_SANDBOX_ENABLED' in env)
    chk('.env.example has VECTOR_MEMORY', 'VECTOR_MEMORY_ENABLED' in env)
except: chk('.env.example readable', False)

chk('.github/FUNDING.yml exists', exists('.github/FUNDING.yml'))
chk('.pre-commit-config.yaml exists', exists('.pre-commit-config.yaml'))
try:
    pc = rd(os.path.join(ROOT, '.pre-commit-config.yaml'))
    chk('pre-commit has ruff hook', 'ruff' in pc)
    chk('pre-commit has bandit hook', 'bandit' in pc)
    chk('pre-commit has detect-private-key', 'detect-private-key' in pc)
except: chk('pre-commit config readable', False)

chk('Makefile exists', exists('Makefile'))
try:
    mk = rd(os.path.join(ROOT, 'Makefile'))
    chk('Makefile has dev target', 'dev:' in mk)
    chk('Makefile has test target', 'test:' in mk)
    chk('Makefile has up target', 'up:' in mk)
    chk('Makefile has lint target', 'lint:' in mk)
    chk('Makefile has check target', 'check:' in mk)
    chk('Makefile has clean target', 'clean:' in mk)
except: chk('Makefile readable', False)

# ─── WAVE 2: Error Classifier ─────────────────────────────────────────────────
section("WAVE 2 — ERROR CLASSIFIER")
try:
    from core.error_classifier import ErrorClassifier, ErrorType
    chk('ErrorClassifier imports', True)
    clf = ErrorClassifier()
    r1 = clf.classify("ModuleNotFoundError: No module named 'requests'")
    chk('ENV_ERROR detected for import error', r1.error_type == ErrorType.ENV_ERROR, r1.error_type)
    r2 = clf.classify("SyntaxError: unexpected EOF while parsing")
    chk('LLM_HALLUCINATION detected for SyntaxError', r2.error_type == ErrorType.LLM_HALLUCINATION, r2.error_type)
    r3 = clf.classify("AssertionError: assert 1 == 2")
    chk('TEST_ISSUE detected for AssertionError', r3.error_type == ErrorType.TEST_ISSUE, r3.error_type)
    r4 = clf.classify("FAIL Required test coverage of 80% not reached. Total coverage: 74%")
    chk('COVERAGE_GAP detected', r4.error_type == ErrorType.COVERAGE_GAP, r4.error_type)
    chk('is_agent_fixable works', isinstance(clf.is_agent_fixable(r1), bool))
    strategy = clf.repair_strategy(r1)
    chk('repair_strategy returns string', strategy in ('test', 'implementation', 'deps', 'escalate'), strategy)
    batch = clf.classify_batch(["SyntaxError: x", "ImportError: y"])
    chk('classify_batch returns list', len(batch) == 2)
    chk('confidence is 0-1 float', 0.0 <= r1.confidence <= 1.0)
except Exception as e:
    chk('ErrorClassifier module', False, str(e)[:120])

# ─── WAVE 2: Reflector ────────────────────────────────────────────────────────
section("WAVE 2 — REFLECTOR")
try:
    from core.reflector import Reflector, ReflectionResult
    chk('Reflector imports', True)
    ref = Reflector()
    r = ref.evaluate('execute', 'def add(a, b):\n    return a + b\n', 'Add two numbers')
    chk('Reflector.evaluate returns ReflectionResult', isinstance(r, ReflectionResult))
    chk('clean code passes', r.passed, str(r.issues[:2]))
    chk('confidence is 0-1', 0.0 <= r.confidence <= 1.0, f'{r.confidence:.2f}')

    r_bad = ref.evaluate('execute', 'def stub():\n    pass\n\ndef todo():\n    # TODO: implement\n    pass\n', 'Complex task')
    chk('stub code fails reflection', not r_bad.passed, str(r_bad.issues[:2]))
    chk('issues list populated', len(r_bad.issues) > 0)
    chk('revised_plan generated on failure', len(r_bad.revised_plan) > 0)
    chk('summary property works', 'FAIL' in r_bad.summary or 'PASS' in r_bad.summary)
except Exception as e:
    chk('Reflector module', False, str(e)[:120])

# ─── WAVE 2: Cost Estimator ───────────────────────────────────────────────────
section("WAVE 2 — COST ESTIMATOR")
try:
    from core.cost_estimator import CostEstimator
    chk('CostEstimator imports', True)
    est = CostEstimator(provider='heuristic')
    e = est.estimate('Add docstrings to all functions')
    chk('estimate() returns CostEstimate', hasattr(e, 'estimated_tokens'))
    chk('heuristic cost is 0', e.estimated_cost_usd == 0.0, str(e.estimated_cost_usd))
    chk('cost_label shows FREE', 'FREE' in e.cost_label, e.cost_label)
    chk('summary property works', e.summary != '')
    chk('breakdown dict populated', len(e.breakdown) > 0)

    est2 = CostEstimator(provider='anthropic')
    e2 = est2.estimate('Refactor authentication for security')
    chk('anthropic has non-zero cost', e2.estimated_cost_usd > 0)
    chk('HIGH complexity detected', e2.estimated_tokens > e.estimated_tokens)

    # Test record_spend
    est2.record_spend('proj_1', 10000)
    spend = est2.get_project_spend('proj_1')
    chk('record_spend tracks correctly', spend['tokens_used'] == 10000, str(spend))
except Exception as e:
    chk('CostEstimator module', False, str(e)[:120])

# ─── WAVE 2: Vector Memory ───────────────────────────────────────────────────
section("WAVE 2 — VECTOR MEMORY")
try:
    from core.vector_memory import VectorMemory
    chk('VectorMemory imports', True)
    vm = VectorMemory(repo_path=ROOT)
    chk('VectorMemory created', True)
    count = vm.index_repository()
    chk('index_repository() indexes files', count > 0, f'{count} files')
    results = vm.search('error classification taxonomy', top_k=3)
    chk('search() returns list', isinstance(results, list))
    if results:
        chk('results have file_path', hasattr(results[0], 'file_path'))
        chk('results have relevance_score 0-1', 0.0 <= results[0].relevance_score <= 1.0)
        chk('results have source', results[0].source in ('vector', 'keyword'))
    results2 = vm.get_context_for_file('core/error_classifier.py')
    chk('get_context_for_file() works', isinstance(results2, list))
    vm.clear()
    chk('clear() resets index', not vm._is_indexed)
except Exception as e:
    chk('VectorMemory module', False, str(e)[:120])

# ─── WAVE 2: P3 Original — Git Agent ─────────────────────────────────────────
section("WAVE 2 — GIT AGENT (P3)")
try:
    from core.git_agent import GitAgent
    chk('GitAgent imports', True)
    ga = GitAgent(repo_path=ROOT)
    result = ga.commit_convergence(
        task_description="Add JWT authentication to user endpoints",
        files_changed=["core/auth.py", "tests/test_auth.py"],
        test_coverage=74.5,
        iterations=3,
        dry_run=True,
    )
    chk('dry_run commit returns result', result.message != '')
    chk('commit type is feat', result.message.startswith('feat'), result.message[:30])
    chk('scope extracted from files', '(core)' in result.message or '(' in result.message, result.message[:40])
    chk('body mentions coverage', '74.5' in result.message, result.message[:100])

    # Test classify_type
    chk('fix type for bug', ga._classify_type('fix login bug') == 'fix')
    chk('docs type for docs', ga._classify_type('update documentation') == 'docs')
    chk('security type for auth', ga._classify_type('security scan') == 'security')
except Exception as e:
    chk('GitAgent module', False, str(e)[:120])

# ─── WAVE 2: P3 Original — Performance Profiler ──────────────────────────────
section("WAVE 2 — PERFORMANCE PROFILER (P3)")
try:
    import time
    from core.performance_profiler import PerformanceProfiler
    chk('PerformanceProfiler imports', True)
    prof = PerformanceProfiler(project_id='test')
    with prof.step('execute', agent='developer', tokens_used=3000):
        time.sleep(0.01)
    with prof.step('validate', agent='qa', tokens_used=1500):
        time.sleep(0.005)
    prof.record('patch', agent='patch_engine', duration_ms=200, tokens_used=2000, success=True)
    report = prof.report()
    chk('report() returns dict', isinstance(report, dict))
    chk('report has total_steps', report.get('total_steps', 0) >= 3, str(report.get('total_steps')))
    chk('report has slowest_step', 'slowest_step' in report, report.get('slowest_step'))
    chk('report has step_stats', 'step_stats' in report)
    chk('report has optimization_hints', isinstance(report.get('optimization_hints'), list))
    health = prof.agent_health()
    chk('agent_health() returns list', isinstance(health, list))
    chk('agent_health has per-agent metrics', len(health) > 0)
except Exception as e:
    chk('PerformanceProfiler module', False, str(e)[:120])

# ─── WAVE 4: Docker Sandbox ───────────────────────────────────────────────────
section("WAVE 4 — DOCKER SANDBOX")
try:
    from sandbox.docker_executor import DockerSandboxExecutor
    chk('DockerSandboxExecutor imports', True)
    exec_ = DockerSandboxExecutor(use_docker=False)  # Force subprocess for CI
    chk('executor created', True)
    chk('subprocess mode when docker=False', not exec_.use_docker)
    chk('_extract_coverage parses TOTAL line', DockerSandboxExecutor._extract_coverage("TOTAL  100  30  70%") == 70.0)
    chk('_extract_coverage handles no coverage', DockerSandboxExecutor._extract_coverage("no coverage here") is None)
except Exception as e:
    chk('DockerSandboxExecutor module', False, str(e)[:120])

# ─── WAVE 4: Docs + Benchmarks ───────────────────────────────────────────────
section("WAVE 4 — DOCS & BENCHMARKS")
chk('docs/ollama_setup.md exists', exists('docs/ollama_setup.md'))
try:
    ollama_doc = rd(os.path.join(ROOT, 'docs', 'ollama_setup.md'))
    chk('Ollama guide has install steps', 'curl' in ollama_doc or 'Install' in ollama_doc)
    chk('Ollama guide has performance table', 'Claude 3.5' in ollama_doc and 'Ollama' in ollama_doc)
    chk('Ollama guide has hardware reqs', 'RAM' in ollama_doc)
except: chk('ollama_setup.md readable', False)

chk('benchmarks/results/ exists', isdir('benchmarks/results'))
import json
for repo_name in ['psf_requests', 'pallets_flask', 'tiangolo_fastapi']:
    path = os.path.join(ROOT, 'benchmarks', 'results', f'{repo_name}.json')
    chk(f'{repo_name}.json exists', os.path.exists(path))
    if os.path.exists(path):
        try:
            data = json.loads(open(path, encoding='utf-8').read())
            chk(f'{repo_name} has result field', 'result' in data, str(data.get('result')))
            chk(f'{repo_name} coverage >= 70', data.get('coverage_achieved', 0) >= 70.0, str(data.get('coverage_achieved')))
        except: chk(f'{repo_name} JSON valid', False)

# ─── WAVE 5: UI Elements ─────────────────────────────────────────────────────
section("WAVE 5 — UI ELEMENTS")
try:
    html = rd(os.path.join(ROOT, 'ui', 'index.html'))
    chk('Benchmarks tab exists', 'data-tab="benchmarks"' in html)
    chk('benchmarks-view div exists', 'id="benchmarks-view"' in html)
    chk('HITL modal exists', 'hitl-modal' in html)
    chk('hitl-approve-btn exists', 'hitl-approve-btn' in html)
    chk('Reasoning Trace panel exists', 'reasoning-trace' in html)
    chk('DAG nodes exist', 'dag-understand' in html)
    chk('Agent Health panel', 'agent-health-panel' in html)
    chk('Theme toggle button', 'theme-toggle-btn' in html)
    chk('Cost estimate banner', 'cost-estimate-banner' in html)
    chk('Memory search bar', 'memory-search-btn' in html)
    chk('HITL confidence slider', 'cfg-hitl' in html)
    chk('Seniority selector', 'cfg-seniority' in html)
    chk('Docker sandbox setting', 'cfg-sandbox' in html)
    chk('5 tabs total', html.count('data-tab=') >= 5)
except: chk('index.html readable', False)

try:
    css = rd(os.path.join(ROOT, 'ui', 'index.css'))
    chk('Agent health CSS', '.agent-health-panel' in css)
    chk('Reasoning trace CSS', '.reasoning-trace' in css)
    chk('DAG node CSS', '.dag-node' in css)
    chk('Benchmark table CSS', '.bench-table' in css)
    chk('Cost banner CSS', '.cost-banner' in css)
    chk('HITL modal CSS', '.hitl-modal' in css)
    chk('Light mode CSS', 'body.light-mode' in css)
    chk('Memory search CSS', '.memory-search-bar' in css)
    chk('Settings grid CSS', '.settings-grid' in css)
    chk('fadeSlideIn animation', 'fadeSlideIn' in css)
except: chk('index.css readable', False)

try:
    js = rd(os.path.join(ROOT, 'ui', 'src', 'main.js'))
    chk('Theme toggle JS', 'theme-toggle-btn' in js)
    chk('Reasoning trace JS', 'addTraceLine' in js)
    chk('DAG update JS', 'updateDAGPhase' in js)
    chk('Benchmarks loading JS', 'loadBenchmarks' in js)
    chk('HITL modal JS', 'showHITLModal' in js)
    chk('Memory search JS', 'memorySearchBtn' in js)
    chk('Vector index JS', 'memory-index-btn' in js)
    chk('handleServerEvent override', 'window.handleServerEvent = handleServerEvent' in js)
    chk('HITL approve API call', '/hitl/' in js)
    chk('Benchmark fallback data', 'psf/requests' in js)
except: chk('main.js readable', False)

# ─── WAVE 3: Claude Flow Integration ─────────────────────────────────────────
section("WAVE 3 — CLAUDE_FLOW INTEGRATION")
try:
    cf = rd(os.path.join(ROOT, 'core', 'claude_flow.py'))
    chk('Reflector imported in claude_flow', 'from core.reflector import Reflector' in cf)
    chk('CostEstimator imported in claude_flow', 'from core.cost_estimator import CostEstimator' in cf)
    chk('ErrorClassifier imported in claude_flow', 'from core.error_classifier import ErrorClassifier' in cf)
    chk('PerformanceProfiler imported in claude_flow', 'from core.performance_profiler import PerformanceProfiler' in cf)
    chk('GitAgent imported in claude_flow', 'from core.git_agent import GitAgent' in cf)
    chk('VectorMemory optional import in claude_flow', 'from core.vector_memory import VectorMemory' in cf)
    chk('_reflector in ClaudeFlow.__init__', 'self._reflector' in cf)
    chk('_cost_est in ClaudeFlow.__init__', 'self._cost_est' in cf)
    chk('_profiler in ClaudeFlow.__init__', 'self._profiler' in cf)
    chk('_git_agent in ClaudeFlow.__init__', 'self._git_agent' in cf)
    chk('Reflector.evaluate called per phase', 'reflection = self._reflector.evaluate' in cf)
    chk('Cost estimate injected before loop', 'cost_estimate = self._cost_est.estimate' in cf)
    chk('VectorMemory injected into understand', "phase_name == \"understand\" and self._vector_memory" in cf)
    chk('Profiler wraps each phase', 'with self._profiler.step' in cf)
    chk('ErrorClassifier applied to issues', 'self._error_clf.classify' in cf)
    chk('GitAgent auto-commit on convergence', 'git_agent.commit_convergence' in cf)
    chk('Performance report in result dict', '"performance": perf_report' in cf)
    chk('estimated_cost_usd in result dict', '"estimated_cost_usd": cost_estimate.estimated_cost_usd' in cf)
except: chk('claude_flow.py readable', False)

# ─── WAVE 3: PatchEngine Integration ─────────────────────────────────────────
section("WAVE 3 — PATCH_ENGINE INTEGRATION")
try:
    pe = rd(os.path.join(ROOT, 'core', 'patch_engine.py'))
    chk('ErrorClassifier imported in patch_engine', 'from core.error_classifier import ErrorClassifier' in pe)
    chk('_classifier = ErrorClassifier()', '_classifier = ErrorClassifier()' in pe)
    chk('auto-classify in patch_test()', 'clf_result = _classifier.classify' in pe)
    chk('repair_strategy used', '_classifier.repair_strategy' in pe)
    chk('is_agent_fixable routing', '_classifier.is_agent_fixable' in pe)
    chk('error_type on PatchResult', 'error_type: str' in pe)
    chk('sets result.error_type', 'result.error_type = clf_result.error_type.value' in pe)
    chk('non-fixable early return', 'Non-fixable:' in pe)
    # Live test
    from core.patch_engine import PatchEngine
    eng = PatchEngine(claude_client=None)
    pr = eng.patch_test(
        original_code='import json_bad\ndef test_x(): pass',
        failure_log="ModuleNotFoundError: No module named 'json_bad'",
    )
    chk('PatchEngine produces PatchResult', hasattr(pr, 'patched_code'))
    chk('PatchResult has error_type field', pr.error_type != '')
    chk('ENV_ERROR auto-detected in patch', 'ENV_ERROR' in pr.error_type.upper() or 'env' in pr.error_type.lower(), pr.error_type)
except Exception as e:
    chk('PatchEngine integration', False, str(e)[:120])

# ─── WAVE 3: Memory Integration ───────────────────────────────────────────────
section("WAVE 3 — MEMORY INTEGRATION")
try:
    mem_src = rd(os.path.join(ROOT, 'core', 'memory.py'))
    chk('AgentMemory.search has VectorMemory branch', 'Wave 3: Also query VectorMemory' in mem_src)
    chk('attach_vector_memory() method added', 'def attach_vector_memory' in mem_src)
    chk('_vector_memory attribute set', 'self._vector_memory = vm' in mem_src)
    from core.memory import AgentMemory
    am = AgentMemory('test_wave3')
    am.add_context('error classification module', tags=['core'])
    results = am.search('error')
    chk('AgentMemory.search still works', any('error' in str(r.content).lower() for r in results))
    am.attach_vector_memory(None)  # Attach None (disabled) — should not crash
    chk('attach_vector_memory(None) safe', True)
except Exception as e:
    chk('Memory integration', False, str(e)[:120])

# ─── WAVE 4 (Extended): docker-compose.yml ───────────────────────────────────
section("WAVE 4 — DOCKER-COMPOSE.YML (EXTENDED)")
try:
    dc = rd(os.path.join(ROOT, 'docker-compose.yml'))
    chk('docker-compose has backend service', 'ae-backend' in dc)
    chk('docker-compose has frontend service', 'ae-frontend' in dc)
    chk('docker-compose has ollama service', 'ae-ollama' in dc or 'ollama/ollama' in dc)
    chk('Ollama behind a profile', 'profiles:' in dc)
    chk('ollama profile named', 'ollama' in dc)
    chk('backend healthcheck present', 'healthcheck' in dc)
    chk('start_period in healthcheck', 'start_period' in dc)
    chk('frontend depends_on backend', 'service_healthy' in dc)
    chk('ChromaDB volume mounted', '.chroma' in dc)
    chk('VECTOR_MEMORY_ENABLED env in compose', 'VECTOR_MEMORY_ENABLED' in dc)
    chk('AUTO_GIT_COMMIT env in compose', 'AUTO_GIT_COMMIT' in dc)
    chk('HITL_CONFIDENCE_THRESHOLD env in compose', 'HITL_CONFIDENCE_THRESHOLD' in dc)
    chk('OLLAMA_HOST configured', 'OLLAMA_HOST' in dc)
    chk('DOCKER_SANDBOX_ENABLED in compose', 'DOCKER_SANDBOX_ENABLED' in dc)
    chk('PORT configurable', '${PORT' in dc or '${PORT:-' in dc)
    chk('ollama_models volume defined', 'ollama_models' in dc)
except: chk('docker-compose.yml readable', False)

# ─── INTEGRATION CHECKS ───────────────────────────────────────────────────────
section("INTEGRATION CHECKS")
try:
    pe = rd(os.path.join(ROOT, 'core', 'patch_engine.py'))
    chk('PII scrubber in patch_engine', 'PIIScrubber' in pe)
    cf = rd(os.path.join(ROOT, 'core', 'claude_flow.py'))
    chk('SLMRouter in claude_flow', 'SLMRouter' in cf)
    chk('HITLManager in claude_flow', 'HITLManager' in cf)
    chk('PIIScrubber in claude_flow', 'PIIScrubber' in cf)
except: chk('Integration wiring readable', False)

print(f"\n{'='*55}")
print(f"  V2 RESULTS: {p} passed / {f} failed  |  Total: {p+f}")
print('='*55)
sys.exit(0 if f == 0 else 1)
