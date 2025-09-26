#!/usr/bin/env python3
"""
Test runner script for Coach AI
Provides different test execution modes and coverage reporting
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n🚀 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found. Make sure pytest is installed: pip install pytest")
        return False


def main():
    parser = argparse.ArgumentParser(description="Coach AI Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--file", "-f", help="Run tests from specific file")
    parser.add_argument("--pattern", "-k", help="Run tests matching pattern")
    parser.add_argument("--markers", "-m", help="Run tests with specific markers")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    
    args = parser.parse_args()
    
    # Install dependencies if requested
    if args.install_deps:
        deps_cmd = [
            sys.executable, "-m", "pip", "install",
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0"
        ]
        if not run_command(deps_cmd, "Installing test dependencies"):
            return 1
        print("\n" + "="*50)
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add test directory
    if args.file:
        cmd.append(args.file)
    else:
        cmd.append("tests/")
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add pattern matching
    if args.pattern:
        cmd.extend(["-k", args.pattern])
    
    # Add marker filtering
    if args.unit:
        cmd.extend(["-m", "not integration"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    elif args.markers:
        cmd.extend(["-m", args.markers])
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend([
            "--cov=.",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ])
    
    # Run tests
    success = run_command(cmd, "Running tests")
    
    if args.coverage and success:
        print(f"\n📊 Coverage report generated in htmlcov/index.html")
    
    # Test summary
    print("\n" + "="*50)
    if success:
        print("🎉 All tests completed successfully!")
        return 0
    else:
        print("💥 Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())