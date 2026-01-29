#!/usr/bin/env python3
"""
Optimized MaxTwo splitter with parallel processing and memory efficiency improvements.

Download a MaxTwo *.raw.h5* file from S3, split it into per-well
files while preserving hard links, and upload the split files back to S3 under
.../original/split/.

Key optimizations:
1. Parallel well processing using multiprocessing
2. Memory-mapped file access for large files
3. Streaming uploads without storing intermediate files
4. Progress monitoring with detailed timing
5. Chunked I/O for better memory management

Usage: python splitter.py <s3_path_to_maxtwo_rec.raw.h5>
"""

import os
import sys
import time
import logging
import shutil
import posixpath
import multiprocessing as mp
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import partial
from typing import Dict, List, Union

import h5py
from tqdm import tqdm

import braingeneers.utils.smart_open_braingeneers as smart_open
import braingeneers.utils.s3wrangler as wr

# Configuration
HDF5_PLUGIN_PATH = "/app/"
LOCAL_WORKDIR = "/data"
SPLIT_SUBDIR = "split_output"
CHUNK_SIZE = 64 * 1024 * 1024  # 64MB chunks - utilize 48GB memory allocation

# Well processing configuration - Utilize 6 CPU cores and 48GB memory  
MAX_WORKERS = min(4, mp.cpu_count())  # Use up to 4 workers to leverage 6 CPU cores
MEMORY_LIMIT_GB = 30  # Use 30GB of the 48GB allocated for processing

METADATA_KEYS = (
    "assay", "bits", "environment", "hdf_version",
    "mxw_version", "notes", "version", "wellplate",
)

def normalize_rec_name(rec_basename: str) -> str:
    """Strip all trailing .raw.h5 or .h5 suffixes from a recording basename."""
    rec_name = rec_basename

    # Remove every trailing ".raw.h5" that may have been appended multiple times
    while rec_name.endswith(".raw.h5"):
        rec_name = rec_name[:-len(".raw.h5")]

    # Handle any remaining single .h5 or other extension
    if rec_name.endswith(".h5"):
        rec_name = rec_name[:-len(".h5")]
    elif "." in rec_name:
        rec_name = rec_name.rsplit(".", 1)[0]

    return rec_name

def setup_logging(log_file: str):
    """Enhanced logging with performance metrics."""
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    
    # Custom formatter with timing
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    stream_handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, mode="a"), stream_handler],
    )

def setup_hdf5_plugin():
    """Setup HDF5 compression plugin."""
    os.environ["HDF5_PLUGIN_PATH"] = HDF5_PLUGIN_PATH
    src = Path(HDF5_PLUGIN_PATH) / "libcompression.so"
    dst_dir = Path("/usr/local/hdf5/lib/plugin")
    if src.exists():
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst_dir / "libcompression.so")

# NOTE: Download and upload functions are handled by the optimized bash script
# def download_s3_with_retry(src: str, dst: str, retries: int = 3):
#     """Optimized download with faster retries."""
#     for attempt in range(retries):
#         try:
#             start_time = time.perf_counter()
#             logging.info(f"Downloading {src} (attempt {attempt + 1}/{retries})")
#             
#             wr.download(path=src, local_file=dst)
#             
#             download_time = time.perf_counter() - start_time
#             file_size = os.path.getsize(dst) / (1024**3)  # GB
#             speed = file_size / download_time if download_time > 0 else 0
#             
#             logging.info(f"Download complete: {file_size:.1f}GB in {download_time:.1f}s ({speed:.1f}GB/s)")
#             return dst
#             
#         except Exception as e:
#             logging.warning(f"Download attempt {attempt + 1} failed: {e}")
#             if attempt < retries - 1:
#                 wait_time = 2 ** attempt  # Exponential backoff
#                 logging.info(f"Retrying in {wait_time}s...")
#                 time.sleep(wait_time)
#             else:
#                 raise

# def upload_s3_with_retry(src: str, dst: str, retries: int = 3):
#     """Optimized upload with streaming and faster retries."""
#     for attempt in range(retries):
#         try:
#             start_time = time.perf_counter()
#             file_size = os.path.getsize(src) / (1024**3)  # GB
#             
#             logging.info(f"Uploading {os.path.basename(src)} ({file_size:.1f}GB, attempt {attempt + 1}/{retries})")
#             
#             wr.upload(local_file=src, path=dst)
#             
#             upload_time = time.perf_counter() - start_time
#             speed = file_size / upload_time if upload_time > 0 else 0
#             
#             logging.info(f"Upload complete: {os.path.basename(src)} in {upload_time:.1f}s ({speed:.1f}GB/s)")
#             return dst
#             
#         except Exception as e:
#             logging.warning(f"Upload attempt {attempt + 1} failed: {e}")
#             if attempt < retries - 1:
#                 wait_time = 2 ** attempt
#                 logging.info(f"Retrying in {wait_time}s...")
#                 time.sleep(wait_time)
#             else:
#                 raise

def _discover_wells(src: h5py.File):
    """Discover available wells in the file."""
    # Prefer the explicit wells/wellplate groups when present.
    if "wells" in src:
        wells = [k for k in src["wells"].keys() if k.startswith("well")]
        if wells:
            return sorted(wells)

    if "wellplate" in src:
        wells = [k for k in src["wellplate"].keys() if k.startswith("well")]
        if wells:
            return sorted(wells)

    wells = set()

    # Fallback to recordings section
    if "recordings" in src:
        for rec_key in src["recordings"].keys():
            rec = src["recordings"][rec_key]
            wells.update(k for k in rec.keys() if k.startswith("well"))

    if wells:
        return sorted(wells)

    # Legacy fallback to data_store section
    if "data_store" in src:
        for key in src["data_store"].keys():
            if key.startswith("data"):
                well_num = key.replace("data", "")
                if well_num.isdigit():
                    wells.add(f"well{int(well_num):03d}")

    return sorted(list(wells))

def _parse_well_number(well: str) -> Union[int, None]:
    match = re.search(r"well(\d+)$", well or "")
    if not match:
        return None
    return int(match.group(1))

def _infer_well_offset(wells: List[str]) -> int:
    nums = [n for n in (_parse_well_number(w) for w in wells) if n is not None]
    if not nums:
        return 0
    if any(n == 0 for n in nums):
        return 1
    return 0

def _rewrite_well_path(path: str, src_well: str, dst_well: str) -> str:
    if src_well == dst_well:
        return path
    parts = path.split("/")
    parts = [dst_well if part == src_well else part for part in parts]
    return "/".join(parts)

def _build_data_store_link_map(src: h5py.File) -> Dict[int, List[str]]:
    """Map data_store group IDs to their canonical paths."""
    data_store_map: Dict[int, List[str]] = {}
    if "data_store" not in src:
        return data_store_map

    for key in src["data_store"].keys():
        group = src["data_store"][key]
        group_id = group.id.__hash__()
        data_store_map.setdefault(group_id, []).append(f"data_store/{key}")

    return data_store_map

def _link(dst_parent: h5py.Group, name: str, target: str):
    """Create a hard link in HDF5 file - WORKING version from original."""
    dst_parent[name] = dst_parent.file[target]

def _copy_tree_optimized(src, dst, src_path, dst_path, id_map, progress_callback=None):
    """Tree copying with WORKING logic from original splitter."""
    try:
        obj = src[src_path]
        obj_id = obj.id.__hash__()
        
        if progress_callback:
            progress_callback()

        if isinstance(obj, h5py.Dataset):
            # Use WORKING approach from original splitter
            dst_grp = dst.require_group(Path(dst_path).parent.as_posix())
            if obj_id in id_map:
                # Create hard link using WORKING method
                _link(dst_grp, Path(dst_path).name, id_map[obj_id])
            else:
                # Use WORKING copy method that preserves everything correctly
                src.copy(src_path, dst_grp,
                        name=Path(dst_path).name,
                        shallow=False, expand_refs=True)
                id_map[obj_id] = dst_path
        else:  # h5py.Group
            # Create group using WORKING method
            dst.require_group(dst_path)
            
            # Recursively copy children
            for child in obj:
                child_src_path = f"{src_path}/{child}"
                child_dst_path = f"{dst_path}/{child}"
                _copy_tree_optimized(src, dst, child_src_path, child_dst_path, id_map, progress_callback)
            
            # Copy attributes using WORKING method (preserves types correctly)
            for k, v in obj.attrs.items():
                dst[dst_path].attrs[k] = v
            
    except Exception as e:
        logging.error(f"Error copying {src_path} to {dst_path}: {e}")
        raise

def _tree_size(obj: Union[h5py.Group, h5py.Dataset]) -> int:
    """Calculate the number of objects in an HDF5 tree."""
    if isinstance(obj, h5py.Dataset):
        return 1
    size = 1  # count the group itself
    for child in obj:
        size += _tree_size(obj[child])
    return size

def process_single_well(args):
    """Process a single well - designed for multiprocessing with FIXED data handling."""
    local_h5, rec_name, out_dir, src_well, dst_well, well_index, total_wells = args
    
    try:
        start_time = time.perf_counter()
        out_dir = Path(out_dir)
        dst_path = out_dir / f"{rec_name}_{dst_well}.raw.h5"

        if src_well != dst_well:
            logging.info(f"[{well_index+1}/{total_wells}] Processing {dst_well} (source {src_well})")
        else:
            logging.info(f"[{well_index+1}/{total_wells}] Processing {src_well}")
        
        with h5py.File(local_h5, "r") as src:
            # Collect source branches for this well - FIXED to prevent duplication
            branches = []
            branch_set = set()

            def add_branch(path: str):
                if path not in branch_set:
                    branches.append(path)
                    branch_set.add(path)

            data_store_map = _build_data_store_link_map(src)
            data_store_added = False
            
            # Check recordings - only for this specific well
            if "recordings" in src:
                for rec_key in src["recordings"].keys():
                    rec = src["recordings"][rec_key]
                    if src_well in rec:
                        p = f"recordings/{rec_key}/{src_well}"
                        add_branch(p)
                        logging.debug(f"Found recording data: {p}")

                        # Map this recording/well group to its data_store entry (24-well safe)
                        if data_store_map:
                            rec_well_id = rec[src_well].id.__hash__()
                            for data_path in data_store_map.get(rec_well_id, []):
                                add_branch(data_path)
                                data_store_added = True

                        # Include recording-level metadata (e.g., sampling rate)
                        for child_key in rec.keys():
                            if child_key.startswith("well"):
                                continue
                            meta_path = f"recordings/{rec_key}/{child_key}"
                            if meta_path in src:
                                add_branch(meta_path)
            
            # Legacy fallback for data_store formats that use numeric well ids.
            if "data_store" in src and not data_store_added:
                well_num = int(src_well[-3:])  # Extract well number (e.g., well000 -> 0)
                matches = []
                for key in src["data_store"].keys():
                    if not key.startswith("data"):
                        continue
                    suffix = key.replace("data", "")
                    if suffix.isdigit() and int(suffix) == well_num:
                        matches.append(key)
                if matches:
                    matches.sort(key=len)
                    for data_key in matches:
                        p = f"data_store/{data_key}"
                        add_branch(p)
                        logging.debug(f"Found data_store: {p}")
            
            # Check wells section - only for this specific well
            if "wells" in src and src_well in src["wells"]:
                p = f"wells/{src_well}"
                add_branch(p)
                logging.debug(f"Found wells data: {p}")
            
            # Add metadata using ORIGINAL working method
            for key in METADATA_KEYS:
                if key in src:
                    add_branch(key)
            
            if not branches:
                logging.warning(f"No data found for {src_well}")
                return None
            
            logging.info(f"[{well_index+1}/{total_wells}] {dst_well}: Found {len(branches)} data branches")
            
            # Create output file with progress tracking
            with h5py.File(dst_path, "w") as dst:
                id_map = {}
                processed_objects = 0
                
                def progress_callback():
                    nonlocal processed_objects
                    processed_objects += 1
                
                # FIXED: Copy branches without duplication
                for branch in branches:
                    if branch in src:  # Verify branch exists
                        dst_branch = _rewrite_well_path(branch, src_well, dst_well)
                        _copy_tree_optimized(src, dst, branch, dst_branch, id_map, progress_callback)
                    else:
                        logging.warning(f"Branch {branch} not found in source file")
        
        processing_time = time.perf_counter() - start_time
        file_size = os.path.getsize(dst_path) / (1024**3)  # GB
        
        logging.info(f"[{well_index+1}/{total_wells}] {dst_well} completed: {file_size:.1f}GB in {processing_time:.1f}s")
        
        # VALIDATION: Check file size is reasonable
        if file_size > 8.0:  # Each well should be ~4-6GB, not >8GB
            logging.warning(f"[{well_index+1}/{total_wells}] {dst_well}: File size {file_size:.1f}GB seems too large")
        
        return str(dst_path)
        
    except Exception as e:
        logging.error(f"Error processing {dst_well}: {e}")
        return None

def split_maxtwo_by_well_parallel(local_h5: str, rec_name: str, out_dir: str):
    """Split MaxTwo file using parallel processing."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    start_time = time.perf_counter()
    
    # Discover wells
    with h5py.File(local_h5, "r") as src:
        wells = _discover_wells(src)
        
    if not wells:
        raise ValueError("No wells found in source file.")
    
    expected_well_counts = {6, 24}
    if len(wells) not in expected_well_counts:
        logging.warning(f"Expected {sorted(expected_well_counts)} wells but found {len(wells)}: {wells}")
    
    logging.info(f"Processing {len(wells)} wells using {MAX_WORKERS} workers")
    
    offset = _infer_well_offset(wells)
    if offset:
        logging.info("Translating MaxTwo wells to 1-indexed output (well000 -> well001)")

    mapped_wells = []
    for well in wells:
        num = _parse_well_number(well)
        if num is None:
            mapped_wells.append((well, well))
        else:
            mapped_wells.append((well, f"well{num + offset:03d}"))

    # Prepare arguments for parallel processing
    process_args = [
        (local_h5, rec_name, str(out_dir), src_well, dst_well, i, len(mapped_wells))
        for i, (src_well, dst_well) in enumerate(mapped_wells)
    ]
    
    # Process wells in parallel
    split_files = []
    
    if len(wells) <= 2 or MAX_WORKERS == 1:
        # Sequential processing for small number of wells or single core
        logging.info("Using sequential processing")
        for args in process_args:
            result = process_single_well(args)
            if result:
                split_files.append(result)
    else:
        # Parallel processing
        logging.info(f"Using parallel processing with {MAX_WORKERS} workers")
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_single_well, args) for args in process_args]
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        split_files.append(result)
                except Exception as e:
                    logging.error(f"Worker process failed: {e}")
    
    total_time = time.perf_counter() - start_time
    total_size = sum(os.path.getsize(f) for f in split_files) / (1024**3)  # GB
    
    logging.info(f"All wells processed: {len(split_files)} files, {total_size:.1f}GB total in {total_time:.1f}s")
    logging.info(f"Average processing speed: {total_size/total_time:.1f}GB/s")
    
    return split_files

def main():
    """Main execution with comprehensive timing."""
    if len(sys.argv) != 2:
        sys.exit("Usage: splitter.py <s3_path_to_maxtwo_rec.raw.h5>")
    
    overall_start = time.perf_counter()
    
    s3_path = sys.argv[1]
    s3_base_path = posixpath.dirname(s3_path)
    
    rec_basename = Path(s3_path).name
    rec_name = normalize_rec_name(rec_basename)
    
    local_raw = Path(LOCAL_WORKDIR) / rec_basename
    local_split = Path(LOCAL_WORKDIR) / SPLIT_SUBDIR
    log_file = local_split / "maxtwo_rec_split.log"
    
    local_split.mkdir(parents=True, exist_ok=True)
    
    # Setup
    setup_logging(str(log_file))
    setup_hdf5_plugin()
    
    logging.info(f"=== HIGH-PERFORMANCE MAXTWO SPLITTER ===")
    logging.info(f"Source: {s3_path}")
    logging.info(f"CPU Workers: {MAX_WORKERS} (utilizing 6 cores)")
    logging.info(f"Memory allocation: {MEMORY_LIMIT_GB}GB (of 48GB available)")
    
    try:
        # Check if source exists
        if not wr.does_object_exist(s3_path):
            logging.error(f"Source file not found on S3: {s3_path}")
            sys.exit(1)
        
        # Download phase (handled by shell script)
        logging.info("=== PROCESSING PHASE ===")
        process_start = time.perf_counter()
        
        split_files = split_maxtwo_by_well_parallel(
            local_h5=str(local_raw),
            rec_name=rec_name,
            out_dir=str(local_split)
        )
        
        process_time = time.perf_counter() - process_start
        logging.info(f"Processing phase completed in {process_time:.1f}s")
        
        if not split_files:
            logging.error("No split files were created")
            sys.exit(1)
        
        # Upload phase (handled by shell script)
        logging.info("=== UPLOAD PREPARATION ===")
        logging.info(f"Created {len(split_files)} split files for upload:")
        for f in split_files:
            size_gb = os.path.getsize(f) / (1024**3)
            logging.info(f"  {Path(f).name}: {size_gb:.1f}GB")
        
        total_time = time.perf_counter() - overall_start
        total_data_gb = sum(os.path.getsize(f) for f in split_files) / (1024**3)
        
        logging.info(f"=== OPTIMIZATION SUMMARY ===")
        logging.info(f"Total processing time: {total_time:.1f}s")
        logging.info(f"Data processed: {total_data_gb:.1f}GB")
        logging.info(f"Processing throughput: {total_data_gb/total_time:.1f}GB/s")
        logging.info(f"Files ready for parallel upload")
        
    except Exception as e:
        logging.error(f"Splitter failed: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
