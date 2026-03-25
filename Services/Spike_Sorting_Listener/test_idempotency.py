#!/usr/bin/env python3
"""
Test script to verify the idempotency check in k8s_kilosort2.py.

Tests that:
1. create_job() skips creation when a job already exists (deduplication)
2. create_job() proceeds normally when no duplicate exists
3. The return value is None for duplicates vs a response for new jobs
"""

import sys
import os
import logging
from unittest.mock import patch, MagicMock, PropertyMock

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def test_idempotency_check():
    """Test that create_job() implements explicit deduplication."""

    print("=" * 60)
    print("TESTING: Job Creation Idempotency Check")
    print("=" * 60)

    # Mock kubernetes modules before importing Kube
    mock_k8s_client = MagicMock()
    mock_k8s_config = MagicMock()

    with patch.dict('sys.modules', {
        'kubernetes': MagicMock(),
        'kubernetes.client': mock_k8s_client,
        'kubernetes.config': mock_k8s_config,
    }):
        from k8s_kilosort2 import Kube

        # --- Test Case 1: Job doesn't exist -> should create ---
        print("\n=== Test Case 1: New Job (no duplicate) ===")

        job_info = {
            "uuid": "test-uuid",
            "experiment": "test.raw.h5",
            "image": "braingeneers/ephys_pipeline:v0.75",
            "args": "./run.sh",
            "cpu_request": 12,
            "memory_request": 64,
            "disk_request": 600,
            "GPU": 1,
        }

        kube = Kube("test-new-job", job_info)

        # Mock: no existing jobs in namespace
        mock_job_list = MagicMock()
        mock_job_list.items = []
        kube.batch_v1.list_namespaced_job.return_value = mock_job_list

        # Mock: successful creation
        mock_response = MagicMock()
        kube.batch_v1.create_namespaced_job.return_value = mock_response

        result = kube.create_job()

        assert result is not None, "Expected response object for new job, got None"
        assert kube.batch_v1.create_namespaced_job.called, "create_namespaced_job should have been called"
        print("PASS: New job was created successfully")

        # --- Test Case 2: Job already exists -> should skip ---
        print("\n=== Test Case 2: Duplicate Job (should skip) ===")

        kube2 = Kube("test-duplicate-job", job_info)

        # Mock: existing job with the same name
        mock_existing_job = MagicMock()
        mock_existing_job.metadata.name = "test-duplicate-job"
        mock_job_list2 = MagicMock()
        mock_job_list2.items = [mock_existing_job]
        kube2.batch_v1.list_namespaced_job.return_value = mock_job_list2

        # Reset mock to track calls
        kube2.batch_v1.create_namespaced_job.reset_mock()

        result = kube2.create_job()

        assert result is None, f"Expected None for duplicate job, got {result}"
        assert not kube2.batch_v1.create_namespaced_job.called, \
            "create_namespaced_job should NOT have been called for duplicate"
        print("PASS: Duplicate job was correctly skipped")

        # --- Test Case 3: Different job name exists -> should create ---
        print("\n=== Test Case 3: Different Job Exists (not a duplicate) ===")

        kube3 = Kube("test-unique-job", job_info)

        # Mock: different job exists
        mock_other_job = MagicMock()
        mock_other_job.metadata.name = "some-other-job"
        mock_job_list3 = MagicMock()
        mock_job_list3.items = [mock_other_job]
        kube3.batch_v1.list_namespaced_job.return_value = mock_job_list3
        kube3.batch_v1.create_namespaced_job.return_value = mock_response

        result = kube3.create_job()

        assert result is not None, "Expected response for unique job, got None"
        assert kube3.batch_v1.create_namespaced_job.called, \
            "create_namespaced_job should have been called for unique job"
        print("PASS: Unique job was created despite other jobs existing")


def test_check_job_exist():
    """Test that check_job_exist() correctly identifies existing jobs."""

    print("\n" + "=" * 60)
    print("TESTING: check_job_exist() Method")
    print("=" * 60)

    mock_k8s_client = MagicMock()
    mock_k8s_config = MagicMock()

    with patch.dict('sys.modules', {
        'kubernetes': MagicMock(),
        'kubernetes.client': mock_k8s_client,
        'kubernetes.config': mock_k8s_config,
    }):
        from k8s_kilosort2 import Kube

        job_info = {
            "uuid": "test-uuid",
            "experiment": "test.raw.h5",
            "image": "braingeneers/ephys_pipeline:v0.75",
            "args": "./run.sh",
            "cpu_request": 12,
            "memory_request": 64,
            "disk_request": 600,
            "GPU": 1,
        }

        # Test: job exists
        print("\n=== Test: Job exists ===")
        kube = Kube("existing-job", job_info)
        mock_job = MagicMock()
        mock_job.metadata.name = "existing-job"
        kube.batch_v1.list_namespaced_job.return_value = MagicMock(items=[mock_job])

        assert kube.check_job_exist() is True, "Should return True for existing job"
        print("PASS: Correctly identified existing job")

        # Test: job doesn't exist
        print("\n=== Test: Job doesn't exist ===")
        kube2 = Kube("nonexistent-job", job_info)
        kube2.batch_v1.list_namespaced_job.return_value = MagicMock(items=[mock_job])

        assert kube2.check_job_exist() is False, "Should return False for nonexistent job"
        print("PASS: Correctly identified nonexistent job")


def main():
    """Run all idempotency tests."""
    print("Testing K8s Job Creation Idempotency")
    print("Verifying: Duplicate jobs are skipped, new jobs are created\n")

    try:
        test_idempotency_check()
        test_check_job_exist()

        print("\n" + "=" * 60)
        print("ALL IDEMPOTENCY TESTS PASSED!")
        print("\nVerified Behavior:")
        print("  1. PASS: New jobs are created normally")
        print("  2. PASS: Duplicate jobs are skipped (return None)")
        print("  3. PASS: Different job names don't trigger false duplicates")
        print("  4. PASS: check_job_exist() correctly identifies existing jobs")
        print("=" * 60)

    except Exception as e:
        print(f"\nFAIL: TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
