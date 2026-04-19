#!/usr/bin/env python3
"""
DeerTeamX Database Connection Diagnostic Script

This script helps diagnose PostgreSQL connection issues.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    print(f"\n🔍 {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"   ✅ Success")
            if result.stdout.strip():
                print(f"   Output:\n{result.stdout}")
            return True, result.stdout
        else:
            print(f"   ❌ Failed (exit code: {result.returncode})")
            if result.stderr.strip():
                print(f"   Error: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False, str(e)


def check_docker_containers():
    """Check if PostgreSQL container is running."""
    print("=" * 70)
    print("Step 1: Checking Docker Containers")
    print("=" * 70)
    
    success, output = run_command(
        ["docker", "ps", "--filter", "ancestor=postgres"],
        "Checking running PostgreSQL containers"
    )
    
    if not success or "postgres" not in output.lower():
        print("\n   ⚠️  No PostgreSQL container found running")
        print("   💡 Try: docker ps -a | grep postgres")
        return False
    
    return True


def check_port_connectivity(port: int = 5433):
    """Check if the PostgreSQL port is accessible."""
    print("\n" + "=" * 70)
    print(f"Step 2: Checking Port {port} Connectivity")
    print("=" * 70)
    
    # Try using nc (netcat)
    success, _ = run_command(
        ["nc", "-zv", "-w", "3", "localhost", str(port)],
        f"Testing connection to localhost:{port}"
    )
    
    if not success:
        # Try telnet as fallback
        print("\n   Trying telnet...")
        success, _ = run_command(
            ["timeout", "3", "bash", "-c", f"echo > /dev/tcp/localhost/{port}"],
            f"Testing with bash TCP redirect"
        )
    
    if not success:
        print(f"\n   ❌ Port {port} is not accessible")
        print("   💡 Check:")
        print("      1. Docker container is running: docker ps")
        print("      2. Port mapping is correct: docker port <container>")
        print("      3. Firewall is not blocking the port")
        return False
    
    return True


def check_database_credentials():
    """Check if database user and database exist."""
    print("\n" + "=" * 70)
    print("Step 3: Checking Database Credentials")
    print("=" * 70)
    
    # Get container name
    result = subprocess.run(
        ["docker", "ps", "--filter", "ancestor=postgres", "--format", "{{.Names}}"],
        capture_output=True,
        text=True
    )
    
    if not result.stdout.strip():
        print("   ❌ No PostgreSQL container found")
        return False
    
    container_name = result.stdout.strip().split('\n')[0]
    print(f"   Using container: {container_name}")
    
    # Try to connect as postgres superuser
    print("\n   Attempting to connect as postgres superuser...")
    success, output = run_command(
        ["docker", "exec", "-it", container_name, "psql", "-U", "postgres", "-c", "\\du"],
        "Listing database users"
    )
    
    if not success:
        print("\n   ❌ Cannot connect to PostgreSQL")
        print("   💡 Check container logs: docker logs <container_name>")
        return False
    
    # Check if deerteamx_user exists
    if "deerteamx_user" in output:
        print("   ✅ User 'deerteamx_user' exists")
    else:
        print("   ⚠️  User 'deerteamx_user' does NOT exist")
        print("   💡 Create it with:")
        print(f"      docker exec -it {container_name} psql -U postgres -c \"CREATE USER deerteamx_user WITH PASSWORD 'deerteamx_password';\"")
    
    # Check if deerteamx_db exists
    success, output = run_command(
        ["docker", "exec", "-it", container_name, "psql", "-U", "postgres", "-c", "\\l"],
        "Listing databases"
    )
    
    if success and "deerteamx_db" in output:
        print("   ✅ Database 'deerteamx_db' exists")
    else:
        print("   ⚠️  Database 'deerteamx_db' does NOT exist")
        print("   💡 Create it with:")
        print(f"      docker exec -it {container_name} psql -U postgres -c \"CREATE DATABASE deerteamx_db OWNER deerteamx_user;\"")
    
    return True


def test_connection_from_env():
    """Test connection using DATABASE_URL from .env.deerteamx."""
    print("\n" + "=" * 70)
    print("Step 4: Testing Connection with DATABASE_URL")
    print("=" * 70)
    
    env_file = Path(__file__).parent.parent / ".env.deerteamx"
    if not env_file.exists():
        print("   ❌ .env.deerteamx not found")
        return False
    
    # Extract DATABASE_URL
    db_url = None
    with open(env_file) as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                db_url = line.split('=', 1)[1].strip()
                break
    
    if not db_url:
        print("   ❌ DATABASE_URL not found in .env.deerteamx")
        return False
    
    print(f"   DATABASE_URL: {db_url}")
    
    # Parse URL components
    try:
        # Simple parsing
        parts = db_url.replace("postgresql://", "").split("@")
        creds = parts[0].split(":")
        host_port_db = parts[1].split("/")
        host_port = host_port_db[0].split(":")
        
        user = creds[0]
        password = creds[1]
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else "5432"
        dbname = host_port_db[1]
        
        print(f"\n   Parsed credentials:")
        print(f"      Host: {host}")
        print(f"      Port: {port}")
        print(f"      User: {user}")
        print(f"      Database: {dbname}")
        
        # Test connection with psql
        print("\n   Testing connection with psql...")
        success, output = run_command(
            ["psql", f"postgresql://{user}:{password}@{host}:{port}/{dbname}", "-c", "SELECT 1;"],
            "Testing PostgreSQL connection"
        )
        
        if success:
            print("   ✅ Connection successful!")
            return True
        else:
            print("   ❌ Connection failed")
            print("   💡 Try manual connection:")
            print(f"      psql '{db_url}'")
            return False
            
    except Exception as e:
        print(f"   ❌ Error parsing URL: {e}")
        return False


def main():
    """Run all diagnostic checks."""
    print("=" * 70)
    print("DeerTeamX Database Connection Diagnostic")
    print("=" * 70)
    
    checks = [
        check_docker_containers,
        lambda: check_port_connectivity(5433),
        check_database_credentials,
        test_connection_from_env,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Check failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total} checks")
    
    if passed == total:
        print("\n🎉 All checks passed! Database should be accessible.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} check(s) failed. Please review the errors above.")
        print("\nCommon fixes:")
        print("  1. Start PostgreSQL container: docker-compose up -d postgres")
        print("  2. Check port mapping: docker port <container_name>")
        print("  3. Create missing user/database (see Step 3 output)")
        print("  4. Verify .env.deerteamx has correct DATABASE_URL")
        return 1


if __name__ == "__main__":
    sys.exit(main())
