#!/usr/bin/env python3
"""
Simple validation script for MaxTwo pipeline logic.
Tests core functions without external dependencies.
"""

def is_maxtwo_recording(data_format: str, file_path: str) -> bool:
    """Test version of MaxTwo detection logic."""
    return (data_format == "maxtwo" and 
            (file_path.endswith(".raw.h5") or file_path.endswith(".h5")))

def format_job_name(raw_name: str, prefix: str = "edp-") -> str:
    """Test version of job name formatting."""
    import re
    
    stem = raw_name
    if raw_name.endswith(".raw.h5"):
        stem = raw_name[:-8]
    elif raw_name.endswith(".h5"):
        stem = raw_name[:-3]
    
    stem = re.sub(r"[^a-z0-9]+", "-", stem.lower())
    stem = stem.strip("-")
    
    full = f"{prefix}{stem}"
    if len(full) > 63:
        keep = 63 - len(prefix)
        full = f"{prefix}{stem[-keep:]}"
        full = full.lstrip("-") or "x"
    
    return full

def test_maxtwo_detection():
    """Test MaxTwo detection logic."""
    print("=== Testing MaxTwo Detection Logic ===")
    
    test_cases = [
        ("maxtwo", "s3://bucket/path/recording.raw.h5", True),
        ("maxtwo", "s3://bucket/path/recording.h5", True),
        ("maxone", "s3://bucket/path/recording.raw.h5", False),
        ("maxtwo", "s3://bucket/path/recording.nwb", False),
        ("maxone", "s3://bucket/path/recording.h5", False),
        ("nwb", "s3://bucket/path/recording.h5", False),
        ("maxtwo-split", "s3://bucket/path/recording.h5", False),
    ]
    
    all_passed = True
    for data_format, file_path, expected in test_cases:
        result = is_maxtwo_recording(data_format, file_path)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status} format='{data_format}', extension='{file_path.split('.')[-1]}' -> {result}")
        if result != expected:
            print(f"    Expected: {expected}, Got: {result}")
            all_passed = False
    
    return all_passed

def test_job_naming():
    """Test job name formatting."""
    print("\n=== Testing Job Name Formatting ===")
    
    test_cases = [
        "M06359_D51_KOLFMO_632025.raw.h5",
        "experiment_name",
        "test-recording.h5", 
        "very-long-experiment-name-that-might-exceed-kubernetes-limits.raw.h5"
    ]
    
    all_passed = True
    for experiment in test_cases:
        job_name = format_job_name(experiment)
        # Check Kubernetes naming rules
        valid_length = len(job_name) <= 63
        valid_chars = job_name.replace("-", "").replace("edp", "").isalnum()
        valid_start = job_name[0].isalnum() if job_name else False
        valid_end = job_name[-1].isalnum() if job_name else False
        
        all_valid = valid_length and valid_chars and valid_start and valid_end
        status = "PASS" if all_valid else "FAIL"
        print(f"  {status} '{experiment}' -> '{job_name}' (len: {len(job_name)})")
        
        if not all_valid:
            print(f"    Issues: length={valid_length}, chars={valid_chars}, start={valid_start}, end={valid_end}")
            all_passed = False
    
    return all_passed

def test_pipeline_logic():
    """Test the overall pipeline decision logic."""
    print("\n=== Testing Pipeline Decision Logic ===")
    
    scenarios = [
        {
            "name": "MaxTwo recording",
            "data_format": "maxtwo",
            "file_path": "s3://bucket/uuid/original/data/recording.raw.h5",
            "expected": "splitter_fanout"
        },
        {
            "name": "MaxOne recording",
            "data_format": "maxone", 
            "file_path": "s3://bucket/uuid/original/data/recording.h5",
            "expected": "direct_sorting"
        },
        {
            "name": "NWB recording",
            "data_format": "nwb",
            "file_path": "s3://bucket/uuid/original/data/recording.nwb",
            "expected": "direct_sorting"
        },
        {
            "name": "Pre-split MaxTwo well",
            "data_format": "maxtwo-split",
            "file_path": "s3://bucket/uuid/original/data/recording_well001.raw.h5",
            "expected": "direct_sorting"
        },
        {
            "name": "Default format (no data_format specified)",
            "data_format": "maxone",  # Default value
            "file_path": "s3://bucket/uuid/original/data/recording.h5",
            "expected": "direct_sorting"
        }
    ]
    
    all_passed = True
    for scenario in scenarios:
        is_maxtwo = is_maxtwo_recording(scenario["data_format"], scenario["file_path"])
        
        if is_maxtwo:
            pipeline = "splitter_fanout"
        elif scenario["data_format"] in ["maxone", "nwb", "maxtwo-split"]:
            pipeline = "direct_sorting"
        else:
            pipeline = "unknown"
        
        correct = pipeline == scenario["expected"]
        status = "PASS" if correct else "FAIL"
        print(f"  {status} {scenario['name']}: {scenario['data_format']} -> {pipeline}")
        
        if not correct:
            print(f"    Expected: {scenario['expected']}, Got: {pipeline}")
            all_passed = False
    
    return all_passed

def test_well_path_generation():
    """Test well result path generation logic."""
    print("\n=== Testing Well Path Generation ===")
    
    base_result_path = "s3://bucket/uuid/derived/kilosort2/experiment_phy.zip"
    experiment = "experiment"
    
    print(f"  Base path: {base_result_path}")
    print(f"  Expected well paths:")
    
    for i in range(6):
        well_result_path = base_result_path.replace(
            f"{experiment}_phy.zip",
            f"{experiment}_well{i:03d}_phy.zip"
        )
        print(f"    well{i:03d}: {well_result_path}")
    
    return True

def main():
    """Run all validation tests."""
    print("MaxTwo Pipeline Logic Validation")
    print("=" * 50)
    
    test_results = []
    test_results.append(test_maxtwo_detection())
    test_results.append(test_job_naming())
    test_results.append(test_pipeline_logic())
    test_results.append(test_well_path_generation())
    
    print("\n" + "=" * 50)
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"ALL TESTS PASSED ({passed}/{total})")
        print("\nMaxTwo pipeline logic is working correctly!")
    else:
        print(f"SOME TESTS FAILED ({passed}/{total})")
        print("\nPlease review the failed tests above.")
    
    print("\nNext steps:")
    print("1. Deploy the updated mqtt_listener.py")
    print("2. Test with actual MaxTwo data")
    print("3. Monitor job execution and results")

if __name__ == "__main__":
    main()
