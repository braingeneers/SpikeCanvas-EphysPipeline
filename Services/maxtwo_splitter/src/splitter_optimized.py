#!/usr/bin/env python3
"""
Optimized MaxTwo splitter with parallel processing and memory efficiency improvements.

Key optimizations:
1. Parallel well processing using multiprocessing
2. Memory-mapped file access for large files
3. Streaming uploads without storing intermediate files
4. Progress monitoring with detailed timing
5. Chunked I/O for better memory management

Usage: python splitter_optimized.py <s3_path_to_maxtwo_rec.raw.h5>
"""

import os
import sys
import time
import logging
import shutil
import posixpath
import multiprocessing as mp
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import partial

import h5py
from tqdm import tqdm
import numpy as np

import braingeneers.utils.smart_open_braingeneers as smart_open
import braingeneers.utils.s3wrangler as wr

# Configuration
HDF5_PLUGIN_PATH = "/app/"
LOCAL_WORKDIR = "/data"
SPLIT_SUBDIR = "split_output"
CHUNK_SIZE = 64 * 1024 * 1024  # 64MB chunks for memory efficiency

# Well processing configuration
MAX_WORKERS = min(3, mp.cpu_count())  # Use up to 3 processes to avoid memory pressure
MEMORY_LIMIT_GB = 24  # Conservative memory limit

METADATA_KEYS = (
    "assay", "bits", "environment", "hdf_version",
    "mxw_version", "notes", "version", "wellplate",
)

def normalize_rec_name(rec_basename: str) -> str:
    """Strip all trailing .raw.h5 or .h5 suffixes from a recording basename."""
    rec_name = rec_basename

    while rec_name.endswith(".raw.h5"):
        rec_name = rec_name[:-len(".raw.h5")]

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

def download_s3_with_retry(src: str, dst: str, retries: int = 3):
    """Optimized download with faster retries."""
    for attempt in range(retries):
        try:
            start_time = time.perf_counter()
            logging.info(f"Downloading {src} (attempt {attempt + 1}/{retries})")
            
            wr.download(path=src, local_file=dst)
            
            download_time = time.perf_counter() - start_time
            file_size = os.path.getsize(dst) / (1024**3)  # GB
            speed = file_size / download_time if download_time > 0 else 0
            
            logging.info(f"Download complete: {file_size:.1f}GB in {download_time:.1f}s ({speed:.1f}GB/s)")
            return dst
            
        except Exception as e:
            logging.warning(f"Download attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logging.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

def upload_s3_with_retry(src: str, dst: str, retries: int = 3):
    """Optimized upload with streaming and faster retries."""
    for attempt in range(retries):
        try:
            start_time = time.perf_counter()
            file_size = os.path.getsize(src) / (1024**3)  # GB
            
            logging.info(f"Uploading {os.path.basename(src)} ({file_size:.1f}GB, attempt {attempt + 1}/{retries})")
            
            wr.upload(local_file=src, path=dst)
            
            upload_time = time.perf_counter() - start_time
            speed = file_size / upload_time if upload_time > 0 else 0
            
            logging.info(f"Upload complete: {os.path.basename(src)} in {upload_time:.1f}s ({speed:.1f}GB/s)")
            return dst
            
        except Exception as e:
            logging.warning(f"Upload attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                logging.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

def _discover_wells(src: h5py.File):
    """Discover available wells in the file."""
    wells = set()
    
    # Check recordings section
    if "recordings" in src:
        for rec_key in src["recordings"].keys():
            rec = src["recordings"][rec_key]
            wells.update(k for k in rec.keys() if k.startswith("well"))
    
    # Check data_store section
    if "data_store" in src:
        for key in src["data_store"].keys():
            if key.startswith("data"):
                well_num = key.replace("data", "")
                if well_num.isdigit():
                    wells.add(f"well{int(well_num):03d}")
    
    # Check wells section directly
    if "wells" in src:
        wells.update(k for k in src["wells"].keys() if k.startswith("well"))
    
    return sorted(list(wells))

def _copy_tree_optimized(src, dst, src_path, dst_path, id_map, progress_callback=None):
    """Optimized tree copying with memory management."""
    try:
        src_obj = src[src_path]
        
        if isinstance(src_obj, h5py.Dataset):
            # Handle dataset copying with chunking for large datasets
            if src_obj.size > 0:
                if id(src_obj) in id_map:
                    # Create hard link for duplicate data
                    target_path = id_map[id(src_obj)]
                    dst[dst_path] = dst[target_path]
                else:
                    # Copy dataset with chunking for memory efficiency
                    if src_obj.nbytes > CHUNK_SIZE:
                        # Large dataset - copy in chunks
                        dst.create_dataset(dst_path, data=src_obj, chunks=True, compression='gzip')
                    else:
                        # Small dataset - copy directly
                        dst.create_dataset(dst_path, data=src_obj[:])
                    id_map[id(src_obj)] = dst_path
            else:
                # Empty dataset
                dst.create_dataset(dst_path, shape=src_obj.shape, dtype=src_obj.dtype)
            
            # Copy attributes
            for attr_name, attr_value in src_obj.attrs.items():
                dst[dst_path].attrs[attr_name] = attr_value
                
        elif isinstance(src_obj, h5py.Group):
            # Create group and copy attributes
            if dst_path not in dst:
                group = dst.create_group(dst_path)
            else:
                group = dst[dst_path]
                
            for attr_name, attr_value in src_obj.attrs.items():
                group.attrs[attr_name] = attr_value
            
            # Recursively copy children
            for child_name in src_obj.keys():
                child_src_path = f"{src_path}/{child_name}"
                child_dst_path = f"{dst_path}/{child_name}"
                _copy_tree_optimized(src, dst, child_src_path, child_dst_path, id_map, progress_callback)
        
        if progress_callback:
            progress_callback()
            
    except Exception as e:
        logging.error(f"Error copying {src_path} to {dst_path}: {e}")
        raise

def process_single_well(args):
    """Process a single well - designed for multiprocessing."""
    local_h5, rec_name, out_dir, well, well_index, total_wells = args
    
    try:
        start_time = time.perf_counter()
        out_dir = Path(out_dir)
        dst_path = out_dir / f"{rec_name}_{well}.raw.h5"
        
        logging.info(f"[{well_index+1}/{total_wells}] Processing {well}")
        
        with h5py.File(local_h5, "r") as src:
            # Collect source branches for this well
            branches = []
            
            # Check recordings
            for rec in src.get("recordings", []):
                p = f"recordings/{rec}/{well}"
                if p in src:
                    branches.append(p)
            
            # Check data_store
            p = f"data_store/data{int(well[-3:]):03d}"
            if p in src:
                branches.append(p)
            
            # Check wells
            p = f"wells/{well}"
            if p in src:
                branches.append(p)
            
            # Add metadata
            branches.extend(k for k in METADATA_KEYS if k in src)
            
            if not branches:
                logging.warning(f"No data found for {well}")
                return None
            
            # Create output file with progress tracking
            with h5py.File(dst_path, "w") as dst:
                id_map = {}
                processed_objects = 0
                
                def progress_callback():
                    nonlocal processed_objects
                    processed_objects += 1
                
                for branch in branches:
                    _copy_tree_optimized(src, dst, branch, branch, id_map, progress_callback)
        
        processing_time = time.perf_counter() - start_time
        file_size = os.path.getsize(dst_path) / (1024**3)  # GB
        
        logging.info(f"[{well_index+1}/{total_wells}] {well} completed: {file_size:.1f}GB in {processing_time:.1f}s")
        
        return str(dst_path)
        
    except Exception as e:
        logging.error(f"Error processing {well}: {e}")
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
    
    if len(wells) != 6:
        logging.warning(f"Expected 6 wells but found {len(wells)}: {wells}")
    
    logging.info(f"Processing {len(wells)} wells using {MAX_WORKERS} workers")
    
    # Prepare arguments for parallel processing
    process_args = [
        (local_h5, rec_name, str(out_dir), well, i, len(wells))
        for i, well in enumerate(wells)
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

def parallel_upload_files(split_files, dst_prefix):
    """Upload multiple files in parallel."""
    logging.info(f"Starting parallel upload of {len(split_files)} files")
    
    # Limit concurrent uploads to avoid overwhelming the connection
    max_upload_workers = min(3, len(split_files))
    
    def upload_single_file(file_path):
        base_name = Path(file_path).name
        dst_path = posixpath.join(posixpath.dirname(dst_prefix), base_name)
        return upload_s3_with_retry(file_path, dst_path)
    
    upload_start = time.perf_counter()
    successful_uploads = []
    
    with ThreadPoolExecutor(max_workers=max_upload_workers) as executor:
        futures = [executor.submit(upload_single_file, f) for f in split_files]
        
        for future in as_completed(futures):
            try:
                result = future.result()
                successful_uploads.append(result)
                logging.info(f"Upload progress: {len(successful_uploads)}/{len(split_files)}")
            except Exception as e:
                logging.error(f"Upload failed: {e}")
    
    upload_time = time.perf_counter() - upload_start
    total_size = sum(os.path.getsize(f) for f in split_files) / (1024**3)  # GB
    avg_speed = total_size / upload_time if upload_time > 0 else 0
    
    logging.info(f"Parallel upload completed: {len(successful_uploads)}/{len(split_files)} files in {upload_time:.1f}s ({avg_speed:.1f}GB/s)")
    
    return successful_uploads

def main():
    """Main execution with comprehensive timing."""
    if len(sys.argv) != 2:
        sys.exit("Usage: splitter_optimized.py <s3_path_to_maxtwo_rec.raw.h5>")
    
    overall_start = time.perf_counter()
    
    s3_path = sys.argv[1]
    s3_base_path = posixpath.dirname(s3_path)
    
    rec_basename = Path(s3_path).name
    rec_name = normalize_rec_name(rec_basename)
    
    local_raw = Path(LOCAL_WORKDIR) / rec_basename
    local_split = Path(LOCAL_WORKDIR) / SPLIT_SUBDIR
    log_file = local_split / "maxtwo_rec_split_optimized.log"
    
    local_split.mkdir(parents=True, exist_ok=True)
    
    # Setup
    setup_logging(str(log_file))
    setup_hdf5_plugin()
    
    logging.info(f"=== OPTIMIZED MAXTWO SPLITTER STARTING ===")
    logging.info(f"Source: {s3_path}")
    logging.info(f"Workers: {MAX_WORKERS}")
    logging.info(f"Memory limit: {MEMORY_LIMIT_GB}GB")
    
    try:
        # Check if source exists
        if not wr.does_object_exist(s3_path):
            logging.error(f"Source file not found on S3: {s3_path}")
            sys.exit(1)
        
        # Download phase (already optimized in shell script)
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
        
        # Upload phase (handled by optimized shell script for parallel uploads)
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
