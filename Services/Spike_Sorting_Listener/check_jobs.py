#!/usr/bin/env python3
"""
Simple script to check current job status and identify issue.
"""

import sys
import os
import logging
import json
from unittest.mock import patch, MagicMock

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_pipeline_logic():
    """Check if the pipeline logic is working correctly."""
    
    print("=" * 60)
    print("CHECKING: Current Pipeline Logic")
    print("=" * 60)
    
    # Mock dependencies to avoid K8s API calls
    with patch.dict('sys.modules', {
        'kubernetes': MagicMock(),
        'kubernetes.client': MagicMock(),
        'kubernetes.config': MagicMock(),
        'k8s_kilosort2': MagicMock(),
        'paho.mqtt.client': MagicMock()
    }):
        from mqtt_listener import JobMessage, is_maxtwo_recording
        
        # Test MaxTwo detection logic first
        print("\n=== Testing MaxTwo Detection ===")
        test_cases = [
            ("maxtwo", "s3://bucket/test.raw.h5", True),
            ("maxtwo", "s3://bucket/test.h5", True),
            ("maxone", "s3://bucket/test.raw.h5", False),
            ("nwb", "s3://bucket/test.nwb", False),
            ("maxtwo-split", "s3://bucket/test.h5", False),
        ]
        
        for data_format, file_path, expected in test_cases:
            result = is_maxtwo_recording(data_format, file_path)
            status = "PASS" if result == expected else "FAIL"
            print(f"  {status} format='{data_format}', path='{file_path}' -> {result}")
        
        # Test pipeline routing
        print("\n=== Testing Pipeline Routing ===")
        
        # Track which functions get called
        pipeline_calls = {
            'spawn_splitter_fanout': [],
            'create_sort': []
        }
        
        def mock_spawn_splitter_fanout(*args):
            pipeline_calls['spawn_splitter_fanout'].append(args)
            print(f"  MaxTwo pipeline called with: {args[0:2]}")
            
        def mock_create_sort(*args):
            pipeline_calls['create_sort'].append(args)
            print(f"  Regular sorting called with: {args}")
        
        # Mock functions
        mock_functions = {
            'spawn_splitter_fanout': mock_spawn_splitter_fanout,
            'create_sort': mock_create_sort,
            'get_splitter_config': lambda: {'test': 'config'},
            'get_sorter_template': lambda: {'test': 'template'},
            'check_exist': lambda path: False,  # No existing results
            's3_basepath': lambda uuid: f"s3://braingeneers/ephys/{uuid}/",
        }
        
        # Test MaxTwo recording
        print("\n--- MaxTwo Recording ---")
        pipeline_calls['spawn_splitter_fanout'].clear()
        pipeline_calls['create_sort'].clear()
        
        message = {
            'uuid': 'test-uuid-maxtwo',
            'overwrite': 'False',
            'ephys_experiments': {
                'test-maxtwo.raw.h5': {
                    'data_format': 'maxtwo',
                    'blocks': [{'path': 'original/data/test-maxtwo.raw.h5'}]
                }
            }
        }
        
        with patch.multiple('mqtt_listener', **mock_functions):
            job_msg = JobMessage("experiments/upload", message)
            job_msg.run_sorting()
        
        print(f"  MaxTwo pipeline calls: {len(pipeline_calls['spawn_splitter_fanout'])}")
        print(f"  Regular sorting calls: {len(pipeline_calls['create_sort'])}")
        
        if len(pipeline_calls['spawn_splitter_fanout']) == 1 and len(pipeline_calls['create_sort']) == 0:
            print("  MaxTwo correctly triggered ONLY MaxTwo pipeline")
        else:
            print("  MaxTwo pipeline routing FAILED")
            
        # Test MaxOne recording  
        print("\n--- MaxOne Recording ---")
        pipeline_calls['spawn_splitter_fanout'].clear()
        pipeline_calls['create_sort'].clear()
        
        message = {
            'uuid': 'test-uuid-maxone',
            'overwrite': 'False',
            'ephys_experiments': {
                'test-maxone.raw.h5': {
                    'data_format': 'maxone',
                    'blocks': [{'path': 'original/data/test-maxone.raw.h5'}]
                }
            }
        }
        
        with patch.multiple('mqtt_listener', **mock_functions):
            job_msg = JobMessage("experiments/upload", message)
            job_msg.run_sorting()
        
        print(f"  MaxTwo pipeline calls: {len(pipeline_calls['spawn_splitter_fanout'])}")
        print(f"  Regular sorting calls: {len(pipeline_calls['create_sort'])}")
        
        if len(pipeline_calls['spawn_splitter_fanout']) == 0 and len(pipeline_calls['create_sort']) == 1:
            print("  MaxOne correctly triggered ONLY regular pipeline")
        else:
            print("  MaxOne pipeline routing FAILED")

def main():
    """Run all checks."""
    try:
        check_pipeline_logic()
        return 0
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
