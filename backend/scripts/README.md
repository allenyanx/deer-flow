# DeerTeamX Backend Scripts

This directory contains utility and operational scripts for DeerTeamX backend management.

## Available Scripts

### 🔍 Verification Scripts

- **`verify_deerteamx_integration.py`** - Verifies that DeerTeamX has been correctly integrated into DeerFlow
  ```bash
  python scripts/verify_deerteamx_integration.py
  ```
  
  Checks:
  - ✅ Environment file (`.env.deerteamx`) exists and has required variables
  - ✅ DeerTeamX module can be imported
  - ✅ Routers are registered in DeerFlow app
  - ✅ Alembic migration configuration is complete

### 📦 Future Scripts (Planned)

- **`migrate_deerteamx.sh`** - One-command database migration wrapper
- **`backup_deerteamx_db.py`** - Database backup utility
- **`cleanup_old_executions.py`** - Clean up old execution records
- **`generate_test_data.py`** - Generate sample teams and executions for testing

## Usage Guidelines

1. **Run from backend root directory**:
   ```bash
   cd /home/ycp/workSpace/ai/games_dev/deer-flow/backend
   python scripts/<script_name>.py
   ```

2. **Make scripts executable** (for .sh files):
   ```bash
   chmod +x scripts/*.sh
   ```

3. **Check script help** (if available):
   ```bash
   python scripts/verify_deerteamx_integration.py --help
   ```

## Adding New Scripts

When adding new scripts to this directory:

1. **Python scripts**: Add appropriate shebang line (`#!/usr/bin/env python3`)
2. **Shell scripts**: Use `#!/bin/bash` and make executable
3. **Documentation**: Update this README with script description
4. **Dependencies**: List any additional dependencies in comments at the top

## Script Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| Verification | Check integration health | `verify_*.py` |
| Migration | Database schema management | `migrate_*.sh` |
| Maintenance | Cleanup, backup, optimization | `cleanup_*.py`, `backup_*.py` |
| Testing | Test data generation, load testing | `generate_*.py` |
| Deployment | Build, package, deploy helpers | `deploy_*.sh` |

---

**Note**: These scripts are meant to be run directly from the command line, not imported as Python modules.
