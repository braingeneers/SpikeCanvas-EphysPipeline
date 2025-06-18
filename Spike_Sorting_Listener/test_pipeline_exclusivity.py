#!/usr/bin/env python3
"""
Test script to verify that MaxTwo recordings ONLY trigger the MaxTwo pipeline 
and NOT the regular sorting pipeline.
"""

import sys
import os
import logging
from unittest.mock import patch, MagicMock, call

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_pipeline_exclusivity():
    """Test that MaxTwo and regular pipelines are mutually exclusive."""
    
    print("=" * 60)
    print("TESTING: Pipeline Exclusivity")
    print("=" * 60)
    
    # Mock all dependencies
    with patch.dict('sys.modules', {
        'kubernetes': MagicMock(),
        'kubernetes.client': MagicMock(),
        'kubernetes.config': MagicMock(),
        'k8s_kilosort2': MagicMock(),
        'paho.mqtt.client': MagicMock()
    }):
        
        from mqtt_listener import JobMessage
        
        # Track which functions get called
        pipeline_calls = {
            'spawn_splitter_fanout': [],
            'create_sort': []
        }
        
        def mock_spawn_splitter_fanout(*args):
            pipeline_calls['spawn_splitter_fanout'].append(args)
            print(f"MaxTwo pipeline called with: {args[0:2]}")  # UUID, experiment
            
        def mock_create_sort(*args):
            pipeline_calls['create_sort'].append(args)
            print(f"Regular sorting called with: {args}")
            
        # Mock all the other functions
        mock_functions = {
            'spawn_splitter_fanout': mock_spawn_splitter_fanout,
            'create_sort': mock_create_sort,
            'get_splitter_config': lambda: {'args': ['test'], 'cpu_request': '1', 'memory_request': '1Gi', 'disk_request': '10Gi', 'GPU': '0', 'image': 'test'},
            'get_sorter_template': lambda: {'test': 'template'},
            'check_all_maxtwo_wells_exist': lambda *args: (False, ['well000']),  # Missing wells
            'check_exist': lambda path: False,  # No existing results
            's3_basepath': lambda uuid: f"s3://braingeneers/ephys/{uuid}/",
        }
        
        # Test Case 1: MaxTwo recording should ONLY trigger MaxTwo pipeline
        print("\n=== Test Case 1: MaxTwo Recording ===")
        pipeline_calls['spawn_splitter_fanout'].clear()
        pipeline_calls['create_sort'].clear()
        
        message = {
            'uuid': 'test-uuid-maxtwo',
            'overwrite': 'False',
            'ephys_experiments': {
                'test-maxtwo.raw.h5': {
                    'data_format': 'maxtwo',
                    'blocks': [{'path': 's3://bucket/test-maxtwo.raw.h5'}]
                }
            }
        }
        
        with patch.multiple('mqtt_listener', **mock_functions):
            job_msg = JobMessage("experiments/upload", message)
            job_msg.run_sorting()
        
        print(f"MaxTwo pipeline calls: {len(pipeline_calls['spawn_splitter_fanout'])}")
        print(f"Regular sorting calls: {len(pipeline_calls['create_sort'])}")
        
        assert len(pipeline_calls['spawn_splitter_fanout']) == 1, f"Expected 1 MaxTwo call, got {len(pipeline_calls['spawn_splitter_fanout'])}"
        assert len(pipeline_calls['create_sort']) == 0, f"Expected 0 regular calls, got {len(pipeline_calls['create_sort'])}"
        print("PASS: MaxTwo recording ONLY triggered MaxTwo pipeline")
        
        # Test Case 2: MaxOne recording should ONLY trigger regular pipeline
        print("\n=== Test Case 2: MaxOne Recording ===")
        pipeline_calls['spawn_splitter_fanout'].clear()
        pipeline_calls['create_sort'].clear()
        
        message = {
            'uuid': 'test-uuid-maxone',
            'overwrite': 'False',
            'ephys_experiments': {
                'test-maxone.raw.h5': {
                    'data_format': 'maxone',
                    'blocks': [{'path': 's3://bucket/test-maxone.raw.h5'}]
                }
            }
        }
        
        with patch.multiple('mqtt_listener', **mock_functions):
            job_msg = JobMessage("experiments/upload", message)
            job_msg.run_sorting()
        
        print(f"MaxTwo pipeline calls: {len(pipeline_calls['spawn_splitter_fanout'])}")
        print(f"Regular sorting calls: {len(pipeline_calls['create_sort'])}")
        
        assert len(pipeline_calls['spawn_splitter_fanout']) == 0, f"Expected 0 MaxTwo calls, got {len(pipeline_calls['spawn_splitter_fanout'])}"
        assert len(pipeline_calls['create_sort']) == 1, f"Expected 1 regular call, got {len(pipeline_calls['create_sort'])}"
        print("PASS: MaxOne recording ONLY triggered regular pipeline")
        
        # Test Case 3: Mixed batch should trigger appropriate pipelines
        print("\n=== Test Case 3: Mixed Batch ===")
        pipeline_calls['spawn_splitter_fanout'].clear()
        pipeline_calls['create_sort'].clear()
        
        message = {
            'uuid': 'test-uuid-mixed',
            'overwrite': 'False',
            'ephys_experiments': {
                'test-maxtwo-1.raw.h5': {
                    'data_format': 'maxtwo',
                    'blocks': [{'path': 's3://bucket/test-maxtwo-1.raw.h5'}]
                },
                'test-maxone-1.raw.h5': {
                    'data_format': 'maxone',
                    'blocks': [{'path': 's3://bucket/test-maxone-1.raw.h5'}]
                },
                'test-maxtwo-2.h5': {
                    'data_format': 'maxtwo',
                    'blocks': [{'path': 's3://bucket/test-maxtwo-2.h5'}]
                },
                'test-nwb-1.nwb': {
                    'data_format': 'nwb',
                    'blocks': [{'path': 's3://bucket/test-nwb-1.nwb'}]
                }
            }
        }
        
        with patch.multiple('mqtt_listener', **mock_functions):
            job_msg = JobMessage("experiments/upload", message)
            job_msg.run_sorting()
        
        print(f"MaxTwo pipeline calls: {len(pipeline_calls['spawn_splitter_fanout'])}")
        print(f"Regular sorting calls: {len(pipeline_calls['create_sort'])}")
        
        assert len(pipeline_calls['spawn_splitter_fanout']) == 2, f"Expected 2 MaxTwo calls, got {len(pipeline_calls['spawn_splitter_fanout'])}"
        assert len(pipeline_calls['create_sort']) == 2, f"Expected 2 regular calls, got {len(pipeline_calls['create_sort'])}"
        print("PASS: Mixed batch correctly routed to appropriate pipelines")
        
        # Test Case 4: Unknown format should be skipped
        print("\n=== Test Case 4: Unknown Format ===")
        pipeline_calls['spawn_splitter_fanout'].clear()
        pipeline_calls['create_sort'].clear()
        
        message = {
            'uuid': 'test-uuid-unknown',
            'overwrite': 'False',
            'ephys_experiments': {
                'test-unknown.txt': {
                    'data_format': 'unknown',
                    'blocks': [{'path': 's3://bucket/test-unknown.txt'}]
                }
            }
        }
        
        with patch.multiple('mqtt_listener', **mock_functions):
            job_msg = JobMessage("experiments/upload", message)
            job_msg.run_sorting()
        
        print(f"MaxTwo pipeline calls: {len(pipeline_calls['spawn_splitter_fanout'])}")
        print(f"Regular sorting calls: {len(pipeline_calls['create_sort'])}")
        
        assert len(pipeline_calls['spawn_splitter_fanout']) == 0, f"Expected 0 MaxTwo calls, got {len(pipeline_calls['spawn_splitter_fanout'])}"
        assert len(pipeline_calls['create_sort']) == 0, f"Expected 0 regular calls, got {len(pipeline_calls['create_sort'])}"
        print("PASS: Unknown format correctly skipped")

def main():
    """Run all pipeline exclusivity tests."""
    print("Testing MaxTwo Pipeline Exclusivity")
    print("Verifying: MaxTwo → MaxTwo Pipeline ONLY")
    print("Verifying: MaxOne/NWB → Regular Pipeline ONLY")
    
    try:
        test_pipeline_exclusivity()
        
        print("\n" + "=" * 60)
        print("PASS: ALL PIPELINE EXCLUSIVITY TESTS PASSED!")
        print("\nVerified Behavior:")
        print("  1. PASS: MaxTwo recordings ONLY trigger MaxTwo pipeline")
        print("  2. PASS: MaxOne recordings ONLY trigger regular pipeline")
        print("  3. PASS: NWB recordings ONLY trigger regular pipeline")
        print("  4. PASS: Mixed batches route correctly")
        print("  5. PASS: Unknown formats are skipped")
        print("\nPIPELINE EXCLUSIVITY IS CORRECT!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nFAIL: PIPELINE EXCLUSIVITY TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
