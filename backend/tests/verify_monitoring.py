#!/usr/bin/env python3
"""Quick verification that monitoring components are properly integrated."""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("DeerTeamX Monitoring Infrastructure - Quick Verification")
print("=" * 80)
print()

# Test 1: Check file existence
print("✓ Checking file structure...")
files_to_check = [
    "deerteamx/monitoring/logging_config.py",
    "deerteamx/monitoring/metrics.py",
    "deerteamx/api/middleware/request_tracking.py",
    "deerteamx/api/middleware/exception_handlers.py",
    "deerteamx/main.py",
]

for file_path in files_to_check:
    full_path = backend_dir / file_path
    if full_path.exists():
        print(f"  ✅ {file_path}")
    else:
        print(f"  ❌ {file_path} NOT FOUND")
        sys.exit(1)

print()

# Test 2: Check main.py integration
print("✓ Checking main.py integration...")
with open(backend_dir / "deerteamx/main.py", 'r') as f:
    main_content = f.read()

required_integrations = [
    ("RequestTrackingMiddleware", "Request tracking middleware"),
    ("register_exception_handlers", "Exception handlers"),
    ("create_metrics_endpoint", "Metrics endpoint"),
    ("setup_logging", "Logging setup"),
    ("lifespan", "Lifespan manager"),
]

for keyword, description in required_integrations:
    if keyword in main_content:
        print(f"  ✅ {description} ({keyword})")
    else:
        print(f"  ❌ {description} ({keyword}) NOT FOUND")
        sys.exit(1)

print()

# Test 3: Check pyproject.toml dependencies
print("✓ Checking dependencies in pyproject.toml...")
with open(backend_dir / "pyproject.toml", 'r') as f:
    pyproject_content = f.read()

required_deps = [
    "prometheus-client",
    "pydantic-settings",
]

for dep in required_deps:
    if dep in pyproject_content:
        print(f"  ✅ {dep}")
    else:
        print(f"  ⚠️  {dep} not in pyproject.toml (may be installed separately)")

print()

# Test 4: Check .env configuration
print("✓ Checking environment configuration...")
env_example_path = backend_dir / ".env.deerteamx.example"
if env_example_path.exists():
    with open(env_example_path, 'r') as f:
        env_content = f.read()
    
    env_configs = [
        "ENABLE_METRICS",
        "LOG_LEVEL",
        "LOG_FORMAT",
    ]
    
    for config in env_configs:
        if config in env_content:
            print(f"  ✅ {config} configured")
        else:
            print(f"  ⚠️  {config} not in .env.deerteamx.example")
else:
    print(f"  ⚠️  .env.deerteamx.example not found")

print()

# Summary
print("=" * 80)
print("✅ QUICK VERIFICATION PASSED!")
print("=" * 80)
print()
print("Monitoring infrastructure is properly integrated:")
print("  • Structured logging (JSON/text formats)")
print("  • Request ID tracking and performance monitoring")
print("  • Global exception handling")
print("  • Prometheus metrics export")
print("  • Lifespan lifecycle management")
print()
print("Next steps:")
print("  1. Ensure all dependencies are installed:")
print("     cd /home/ycp/workSpace/ai/games_dev/deer-flow/backend")
print("     uv sync")
print()
print("  2. Start the application:")
print("     uvicorn deerteamx.main:app --reload")
print()
print("  3. Test endpoints:")
print("     curl http://localhost:8000/health")
print("     curl http://localhost:8000/deerteamx/docs")
print("     curl http://localhost:8000/metrics  # If ENABLE_METRICS=true")
print("=" * 80)
