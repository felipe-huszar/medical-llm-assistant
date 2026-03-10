#!/usr/bin/env python3
"""
Test runner for Medical LLM Assistant E2E tests.
Executes all test suites and generates report.
"""

import sys
import os
import subprocess
import json
from datetime import datetime

# Add project to path
project_root = "/root/.openclaw/workspace/projects/tech-challenge-fase3"
os.chdir(project_root)
sys.path.insert(0, project_root)

# Set environment variables
os.environ["USE_MOCK_LLM"] = "true"
os.environ["PYTHONPATH"] = project_root

def run_tests():
    """Run all test suites and capture results."""
    
    test_suites = [
        ("Unit Tests", "tests/unit"),
        ("Integration Tests", "tests/integration"),
        ("E2E Tests - Core", "tests/e2e/test_full_journeys.py"),
        ("E2E Tests - Pipeline", "tests/e2e/test_pipeline_e2e.py"),
        ("E2E Tests - Extended", "tests/e2e/test_extended_e2e.py"),
    ]
    
    results = []
    all_passed = True
    
    print("=" * 70)
    print("MEDICAL LLM ASSISTANT - TEST EXECUTION REPORT")
    print(f"Timestamp: {datetime.utcnow().isoformat()} UTC")
    print("Model: MockLLM (USE_MOCK_LLM=true)")
    print("=" * 70)
    print()
    
    for suite_name, test_path in test_suites:
        print(f"\n{'─' * 70}")
        print(f"Running: {suite_name}")
        print(f"Path: {test_path}")
        print('─' * 70)
        
        try:
            # Run pytest with verbose output
            cmd = [
                sys.executable, "-m", "pytest",
                test_path,
                "-v",
                "--tb=short",
                "--color=yes",
                "-x"  # Stop on first failure
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=project_root
            )
            
            passed = result.returncode == 0
            all_passed = all_passed and passed
            
            # Parse results
            output = result.stdout + result.stderr
            
            # Count tests
            import re
            passed_match = re.search(r'(\d+) passed', output)
            failed_match = re.search(r'(\d+) failed', output)
            error_match = re.search(r'(\d+) error', output)
            
            passed_count = int(passed_match.group(1)) if passed_match else 0
            failed_count = int(failed_match.group(1)) if failed_match else 0
            error_count = int(error_match.group(1)) if error_match else 0
            
            results.append({
                "suite": suite_name,
                "path": test_path,
                "passed": passed,
                "passed_count": passed_count,
                "failed_count": failed_count,
                "error_count": error_count,
                "output": output[-2000:] if len(output) > 2000 else output  # Last 2000 chars
            })
            
            # Print summary
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"\n{status} - {passed_count} passed, {failed_count} failed, {error_count} errors")
            
            if not passed:
                print("\n--- Failure Output (last 1000 chars) ---")
                print(output[-1000:])
                
        except subprocess.TimeoutExpired:
            print("❌ TIMEOUT - Test suite took too long")
            results.append({
                "suite": suite_name,
                "path": test_path,
                "passed": False,
                "error": "Timeout"
            })
            all_passed = False
        except Exception as e:
            print(f"❌ ERROR - {e}")
            results.append({
                "suite": suite_name,
                "path": test_path,
                "passed": False,
                "error": str(e)
            })
            all_passed = False
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    total_passed = sum(r.get("passed_count", 0) for r in results)
    total_failed = sum(r.get("failed_count", 0) for r in results)
    total_errors = sum(r.get("error_count", 0) for r in results)
    
    for r in results:
        status = "✅" if r.get("passed") else "❌"
        print(f"{status} {r['suite']}: {r.get('passed_count', 0)} passed")
    
    print()
    print(f"Total: {total_passed} passed, {total_failed} failed, {total_errors} errors")
    print(f"Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    # Save report
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "model": "MockLLM",
        "environment": "test",
        "summary": {
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_errors": total_errors,
            "all_passed": all_passed
        },
        "suites": results
    }
    
    report_path = os.path.join(project_root, "test_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport saved to: {report_path}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(run_tests())
