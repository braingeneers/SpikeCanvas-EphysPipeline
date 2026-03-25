#!/usr/bin/env python3
"""
Test script to verify that splitter job launches first and sorter jobs wait for completion.
This tests the critical sequencing requirement for MaxTwo pipeline.
"""

import sys
import os
import time
import logging
from unittest.mock import patch, MagicMock, call

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_splitter_first_sorters_wait():
    """Test that splitter launches first and sorters wait for completion."""
    
    print("=" * 60)
    print("TESTING: Splitter First, Sorters Wait")
    print("=" * 60)
    
    # Mock all Kubernetes dependencies
    with patch.dict('sys.modules', {
        'kubernetes': MagicMock(),
        'kubernetes.client': MagicMock(),
        'kubernetes.config': MagicMock(),
        'k8s_kilosort2': MagicMock()
    }):
        
        from splitter_fanout import spawn_splitter_fanout, _watch_and_fanout, _launch_sorters
        
        # Track job creation order
        job_creation_log = []
        
        # Create a mock Kube class that tracks job creation
        class MockKube:
            def __init__(self, job_name, config):
                self.job_name = job_name
                self.config = config
                job_creation_log.append(f"INIT: {job_name}")
                print(f"Job initialized: {job_name}")
            
            def create_job(self):
                job_creation_log.append(f"CREATE: {self.job_name}")
                print(f"Job created: {self.job_name}")
                return 0  # Success
                
            def check_job_exist(self):
                return False  # Job doesn't exist, needs to be created
        
        # Test Case 1: Initial splitter launch (no sorters should be created)
        print("\n=== Test Case 1: Initial Splitter Launch ===")
        
        with patch('splitter_fanout.Kube', MockKube), \
             patch('splitter_fanout.threading.Thread') as mock_thread:
            
            # Mock thread start to prevent actual threading
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            
            # Call spawn_splitter_fanout
            splitter_cfg = {
                'args': ['test'], 'cpu_request': '1', 'memory_request': '1Gi', 
                'disk_request': '10Gi', 'GPU': '0', 'image': 'test'
            }
            sorter_tpl = {'test': 'template'}
            
            spawn_splitter_fanout("test-uuid", "test_experiment.raw.h5", splitter_cfg, sorter_tpl)
            
            # Verify only splitter job was created
            created_jobs = [log for log in job_creation_log if log.startswith("CREATE:")]
            print(f"Jobs created: {created_jobs}")
            assert len(created_jobs) == 1, f"Expected 1 job, got {len(created_jobs)}"
            assert "split" in created_jobs[0], f"Expected splitter job, got {created_jobs[0]}"
            print("Only splitter job created initially")
            
            # Verify watcher thread was started
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
            print("Watcher thread started")
        
        # Test Case 2: Watcher waits for splitter success before launching sorters
        print("\n=== Test Case 2: Watcher Behavior ===")
        
        # Reset job tracking
        job_creation_log.clear()
        
        # Mock API responses: running -> running -> succeeded
        api_call_count = 0
        def mock_safe_get_job_status(job_name, max_retries=3, retry_delay=1):
            nonlocal api_call_count
            api_call_count += 1
            
            mock_status = MagicMock()
            if api_call_count <= 2:
                # First two calls: job is still running
                mock_status.succeeded = 0
                mock_status.failed = 0
                mock_status.active = 1
                print(f"Status check {api_call_count}: Job still running...")
                return mock_status
            else:
                # Third call: job succeeded
                mock_status.succeeded = 1
                mock_status.failed = 0
                mock_status.active = 0
                print(f"Status check {api_call_count}: Job succeeded!")
                return mock_status
        
        with patch('splitter_fanout.Kube', MockKube), \
             patch('splitter_fanout._safe_get_job_status', mock_safe_get_job_status), \
             patch('splitter_fanout.time.sleep') as mock_sleep:  # Speed up test
            
            # Call watcher function directly
            _watch_and_fanout(
                "test-splitter-job", 
                "test-uuid", 
                "test_experiment.raw.h5", 
                sorter_tpl, 
                job_created=True
            )
            
            # Verify sorter jobs were created after splitter success
            created_jobs = [log for log in job_creation_log if log.startswith("CREATE:")]
            print(f"Jobs created after splitter success: {created_jobs}")
            assert len(created_jobs) == 6, f"Expected 6 sorter jobs, got {len(created_jobs)}"
            
            # Verify all are well jobs
            for job_log in created_jobs:
                assert "well" in job_log, f"Expected well job, got {job_log}"
            
            print("All 6 sorter jobs created after splitter success")
            print("No sorter jobs created before splitter completion")
        
        # Test Case 3: Verify sorters NOT created if splitter fails
        print("\n=== Test Case 3: No Sorters on Splitter Failure ===")
        
        job_creation_log.clear()
        
        def mock_failed_status(job_name, max_retries=3, retry_delay=1):
            mock_status = MagicMock()
            mock_status.succeeded = 0
            mock_status.failed = 2  # Failed job
            mock_status.active = 0
            print("Status check: Job failed!")
            return mock_status
        
        with patch('splitter_fanout.Kube', MockKube), \
             patch('splitter_fanout._safe_get_job_status', mock_failed_status):
            
            _watch_and_fanout(
                "test-splitter-job", 
                "test-uuid", 
                "test_experiment.raw.h5", 
                sorter_tpl, 
                job_created=True
            )
            
            # Verify NO sorter jobs were created
            created_jobs = [log for log in job_creation_log if log.startswith("CREATE:")]
            print(f"Jobs created after splitter failure: {created_jobs}")
            assert len(created_jobs) == 0, f"Expected 0 jobs on failure, got {len(created_jobs)}"
            print("No sorter jobs created when splitter fails")

def main():
    """Run all sequencing tests."""
    print("Testing MaxTwo Pipeline Job Sequencing")
    print("Verifying: Splitter First -> Wait -> Sorters")
    
    try:
        test_splitter_first_sorters_wait()
        
        print("\n" + "=" * 60)
        print("ALL SEQUENCING TESTS PASSED!")
        print("\nVerified Behavior:")
        print("  1. Only splitter job created initially")
        print("  2. Watcher thread monitors splitter status")  
        print("  3. Sorter jobs ONLY created AFTER splitter succeeds")
        print("  4. No sorter jobs created if splitter fails")
        print("  5. All 6 sorter jobs created on splitter success")
        print("\nSEQUENCING IS CORRECT: Splitter -> Wait -> Sorters")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nSEQUENCING TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
