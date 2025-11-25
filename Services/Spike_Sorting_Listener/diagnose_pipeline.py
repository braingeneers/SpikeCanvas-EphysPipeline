#!/usr/bin/env python3
"""
Diagnostic script to help identify why both splitter and regular sorter jobs are appearing.
"""

print("=== DIAGNOSTIC: MaxTwo Pipeline Issue ===")
print()

print("POSSIBLE CAUSES:")
print("1. Multiple MQTT listeners running (old + new code)")
print("2. Updated code not deployed to production")
print("3. Multiple MQTT messages with different data_format values")
print("4. CSV job processing creating additional jobs")
print()

print("NEXT STEPS TO DIAGNOSE:")
print()

print("1. CHECK RUNNING MQTT LISTENERS:")
print("   kubectl get pods -n braingeneers | grep mqtt")
print("   kubectl get deployment -n braingeneers | grep mqtt")
print()

print("2. CHECK CURRENT CODE VERSION IN PRODUCTION:")
print("   kubectl exec <mqtt-listener-pod> -n braingeneers -- cat /app/src/mqtt_listener.py | grep -A 10 -B 5 'elif fmt in'")
print()

print("3. CHECK MQTT LISTENER LOGS:")
print("   kubectl logs <mqtt-listener-pod> -n braingeneers | grep -E '(MaxTwo|data_format|spawn_splitter|create_sort)'")
print()

print("4. CHECK ALL CURRENT JOBS:")
print("   kubectl get jobs -n braingeneers | grep edp-")
print()

print("5. CHECK JOB NAMES TO IDENTIFY TYPES:")
print("   - Splitter jobs: edp-*-split")
print("   - Well sorter jobs: edp-*-well000, edp-*-well001, etc.")  
print("   - Regular sorter jobs: edp-* (without -split or -well suffix)")
print()

print("6. VERIFY PIPELINE LOGIC:")
print("   The code should have this structure:")
print("   if is_maxtwo_recording(fmt, file_path):")
print("       # MaxTwo pipeline - spawn_splitter_fanout")
print("   elif fmt in ['maxone', 'nwb', 'maxtwo-split']:")
print("       # Regular pipeline - create_sort")
print()

print("If you see job names like 'edp-d57-kolf2-2j-...' (without -well suffix),")
print("those are regular sorter jobs that should NOT exist for MaxTwo recordings.")
print()

print("IMMEDIATE ACTION:")
print("Run: kubectl get jobs -n braingeneers | grep edp- | grep -v split | grep -v well")
print("This will show any regular sorter jobs that shouldn't exist for MaxTwo data.")
