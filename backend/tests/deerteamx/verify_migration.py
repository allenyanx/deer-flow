#!/usr/bin/env python3
"""Quick verification of migration status."""

import subprocess
import sys

print("=" * 80)
print("Verifying Alembic Migration Status")
print("=" * 80)

# Check current version
print("\n1. Checking current migration version...")
result = subprocess.run(
    ["uv", "run", "alembic", "current"],
    capture_output=True,
    text=True,
    cwd="/home/ycp/workSpace/ai/games_dev/deer-flow/backend"
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Check if team_locks table exists
print("\n2. Checking team_locks table...")
result = subprocess.run(
    ["python", "test_db_connection.py"],
    capture_output=True,
    text=True,
    cwd="/home/ycp/workSpace/ai/games_dev/deer-flow/backend"
)
print(result.stdout)
if result.returncode != 0:
    print("ERROR:", result.stderr)

print("\n" + "=" * 80)
print("Verification Complete")
print("=" * 80)
