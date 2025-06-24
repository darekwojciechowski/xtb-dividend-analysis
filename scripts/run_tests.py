#!/usr/bin/env python3
"""
Simple test runner script for the XTB Dividend Analysis project.
Run this script to execute all tests with coverage reporting.
"""

import subprocess
import sys
import os


def run_command(command, description):
    """Run a command and print its output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(command, shell=True, check=True,
                                capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    """Main test runner function."""
    print("🧪 XTB Dividend Analysis - Test Runner")
    # Change to the project directory (parent of scripts directory)
    print("====================================")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    os.chdir(project_dir)
    print(f"Working directory: {project_dir}")

    # List of test commands to run
    test_commands = [
        ("python -m pytest --version", "Checking pytest installation"),
        ("python -m pytest tests/ -v", "Running all tests"),
        ("python -m pytest tests/ -v --cov=data_processing --cov=data_acquisition --cov=visualization --cov=config --cov-report=term-missing",
         "Running tests with coverage"),        ("python -c \"import data_processing.dataframe_processor; print('dataframe_processor imports successfully')\"",
                                                 "Testing module imports"),
    ]

    results = []
    for command, description in test_commands:
        success = run_command(command, description)
        results.append((description, success))

    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")

    all_passed = True
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {description}")
        if not success:
            all_passed = False

    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
