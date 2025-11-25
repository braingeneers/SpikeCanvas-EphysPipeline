#!/usr/bin/env python3
"""
Quick validation script to ensure all imports work and functions are accessible.
This catches any syntax errors or import issues before deployment.
"""

import sys
import os

# Add the src directory to Python path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported without errors."""
    print("Testing imports...")
    
    try:
        # Test job_utils import
        from job_utils import format_job_name, JOB_PREFIX, NAMESPACE, DEFAULT_S3_BUCKET
        print("job_utils imported successfully")
        
        # Test job name formatting
        test_name = format_job_name("test-experiment-well001", prefix="spike-")
        print(f"Job name formatting works: {test_name}")
        
        # Test constants
        print(f"Constants accessible: {JOB_PREFIX}, {NAMESPACE}, {DEFAULT_S3_BUCKET}")
        
    except Exception as e:
        print(f"job_utils import failed: {e}")
        return False
    
    try:
        # Test mqtt_listener import (mock kubernetes dependencies)
        import unittest.mock
        with unittest.mock.patch.dict('sys.modules', {
            'kubernetes': unittest.mock.MagicMock(),
            'kubernetes.client': unittest.mock.MagicMock(),
            'kubernetes.config': unittest.mock.MagicMock(),
            'k8s_kilosort2': unittest.mock.MagicMock()
        }):
            from mqtt_listener import is_maxtwo_recording, get_splitter_config, get_sorter_template
            print("mqtt_listener functions imported successfully")
            
            # Test MaxTwo detection
            assert is_maxtwo_recording("maxtwo", "test.raw.h5") == True
            assert is_maxtwo_recording("maxone", "test.raw.h5") == False  
            assert is_maxtwo_recording("maxtwo", "test.txt") == False
            print("is_maxtwo_recording logic works correctly")
            
    except Exception as e:
        print(f"mqtt_listener import failed: {e}")
        return False
    
    try:
        # Test splitter_fanout import
        with unittest.mock.patch.dict('sys.modules', {
            'kubernetes': unittest.mock.MagicMock(),
            'kubernetes.client': unittest.mock.MagicMock(), 
            'kubernetes.config': unittest.mock.MagicMock(),
            'k8s_kilosort2': unittest.mock.MagicMock()
        }):
            from splitter_fanout import spawn_splitter_fanout, _safe_get_job_status
            print("splitter_fanout functions imported successfully")
            
    except Exception as e:
        print(f"splitter_fanout import failed: {e}")
        return False
    
    return True

def test_logic():
    """Test core logic functions."""
    print("\nTesting core logic...")
    
    try:
        # Mock kubernetes for testing
        import unittest.mock
        with unittest.mock.patch.dict('sys.modules', {
            'kubernetes': unittest.mock.MagicMock(),
            'kubernetes.client': unittest.mock.MagicMock(),
            'kubernetes.config': unittest.mock.MagicMock(),
            'k8s_kilosort2': unittest.mock.MagicMock()
        }):
            from mqtt_listener import is_maxtwo_recording
            
            # Test various combinations
            test_cases = [
                ("maxtwo", "experiment.raw.h5", True),
                ("maxtwo", "experiment.h5", True),
                ("maxtwo", "experiment.txt", False),
                ("maxone", "experiment.raw.h5", False),
                ("nwb", "experiment.raw.h5", False),
                ("maxtwo-split", "experiment.raw.h5", False),
                (None, "experiment.raw.h5", False),  # defaults to maxone
                ("", "experiment.raw.h5", False),   # defaults to maxone
            ]
            
            for data_format, file_path, expected in test_cases:
                result = is_maxtwo_recording(data_format, file_path)
                if result != expected:
                    print(f"FAILED: {data_format}, {file_path} -> {result}, expected {expected}")
                    return False
                else:
                    print(f"PASSED: {data_format}, {file_path} -> {result}")
                    
    except Exception as e:
        print(f"Logic test failed: {e}")
        return False
    
    return True

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("MaxTwo Pipeline Validation")
    print("=" * 60)
    
    success = True
    
    if not test_imports():
        success = False
        
    if not test_logic():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("ALL VALIDATION TESTS PASSED")
        print("The MaxTwo pipeline is ready for deployment!")
    else:
        print("VALIDATION FAILED")
        print("Please fix the issues before deployment.")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
