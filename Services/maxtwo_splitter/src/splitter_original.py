#!/usr/bin/env python3
"""
Download a 6-well MaxTwo *.raw.h5* file from S3, split it into six single-well
files while preserving hard links, and upload the split files back to S3 under
…/original/split/.

Usage
-----
python split_maxtwo.py s3://bucket/…/original/data/<file>.raw.h5
"""

# ----------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------
from pathlib import Path
import os
import sys
import time
import logging
import shutil
import posixpath

import h5py
from tqdm import tqdm

import braingeneers.utils.smart_open_braingeneers as smart_open  # noqa: F401
import braingeneers.utils.s3wrangler as wr

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
HDF5_PLUGIN_PATH = "/app/"          # location of libcompression.so in image
LOCAL_WORKDIR    = "/data"          # Docker-volume mount point
SPLIT_SUBDIR     = "split_output"

METADATA_KEYS = (
    "assay", "bits", "environment", "hdf_version",
    "mxw_version", "notes", "version", "wellplate",
)

# ----------------------------------------------------------------------
# Logging & HDF5 plugin helpers
# ----------------------------------------------------------------------
def setup_logging(log_file: str):
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        handlers=[logging.FileHandler(log_file, mode="a"), stream_handler],
    )

def setup_hdf5_plugin():
    os.environ["HDF5_PLUGIN_PATH"] = HDF5_PLUGIN_PATH
    src = Path(HDF5_PLUGIN_PATH) / "libcompression.so"
    dst_dir = Path("/usr/local/hdf5/lib/plugin")
    if src.exists():
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst_dir / "libcompression.so")

# ----------------------------------------------------------------------
# S3 helpers with exponential-backoff retry
# ----------------------------------------------------------------------
def download_s3_with_retry(src: str, dst: str, retries: int = 5):
    for attempt in range(1, retries + 1):
        try:
            logging.info(f"Downloading {src} → {dst}")
            wr.download(src, dst)
            return
        except Exception as e:
            wait = 2 ** attempt
            logging.warning(
                f"Download failed ({attempt}/{retries}): {e}. Retrying in {wait}s."
            )
            time.sleep(wait)
    raise RuntimeError(f"Failed to download {src} after {retries} attempts.")

def upload_s3_with_retry(src: str, dst: str, retries: int = 5):
    for attempt in range(1, retries + 1):
        try:
            wr.upload(local_file=src, path=dst)
            logging.info(f"Uploaded {src} → {dst}")
            return
        except Exception as e:
            wait = 2 ** attempt
            logging.warning(
                f"Upload failed ({attempt}/{retries}): {e}. Retrying in {wait}s."
            )
            time.sleep(wait)
    raise RuntimeError(f"Failed to upload {src} after {retries} attempts.")

# ----------------------------------------------------------------------
# HDF5 tree-copy helpers (preserve hard links)
# ----------------------------------------------------------------------
def _discover_wells(src: h5py.File):
    wells = set()
    for rec in src.get("recordings", []):
        for gname in src[f"recordings/{rec}"]:
            if gname.startswith("well"):
                wells.add(gname)
    return sorted(wells)

def _link(dst_parent: h5py.Group, name: str, target: str):
    dst_parent[name] = dst_parent.file[target]

def _copy_tree(src, dst, src_path, dst_path, id_map, bar):
    obj    = src[src_path]
    obj_id = obj.id.__hash__()
    bar.update()

    if isinstance(obj, h5py.Dataset):
        dst_grp = dst.require_group(Path(dst_path).parent.as_posix())
        if obj_id in id_map:
            _link(dst_grp, Path(dst_path).name, id_map[obj_id])
        else:
            src.copy(src_path, dst_grp,
                     name=Path(dst_path).name,
                     shallow=False, expand_refs=True)
            id_map[obj_id] = dst_path
    else:  # h5py.Group
        dst.require_group(dst_path)
        for child in obj:
            _copy_tree(src, dst,
                       f"{src_path}/{child}",
                       f"{dst_path}/{child}",
                       id_map, bar)
        for k, v in obj.attrs.items():
            dst[dst_path].attrs[k] = v

def _tree_size(obj: h5py.Group | h5py.Dataset) -> int:
    if isinstance(obj, h5py.Dataset):
        return 1                               # a dataset counts as one
    size = 1                                   # count the group itself
    for child in obj:
        size += _tree_size(obj[child])         # recurse
    return size

# ----------------------------------------------------------------------
# Splitter
# ----------------------------------------------------------------------
def split_maxtwo_by_well(local_h5: str, rec_name: str, out_dir: str):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with h5py.File(local_h5, "r") as src:
        wells = _discover_wells(src)
        if not wells:
            raise ValueError("No wells found in source file.")
        
        if len(wells) != 6:
            raise ValueError(f"Expected 6 wells but found {len(wells)}: {wells}")

        for well in tqdm(wells, desc="Splitting wells", unit="well"):
            dst_path = out_dir / f"{rec_name}_{well}.raw.h5"

            # collect source branches for this well
            branches = []
            for rec in src.get("recordings", []):
                p = f"recordings/{rec}/{well}"
                if p in src:
                    branches.append(p)

            p = f"data_store/data0{int(well[-3:]):03d}"
            if p in src:
                branches.append(p)

            p = f"wells/{well}"
            if p in src:
                branches.append(p)

            branches.extend(k for k in METADATA_KEYS if k in src)
            total_objs = sum(_tree_size(src[b]) for b in branches)

            start = time.perf_counter()
            with h5py.File(dst_path, "w") as dst, \
                 tqdm(total=total_objs,
                      desc=f"{well} obj",
                      unit="obj",
                      leave=False) as bar:

                id_map = {}
                for branch in tqdm(branches,
                                   desc=f"{well} branches",
                                   unit="branch",
                                   leave=False):
                    _copy_tree(src, dst, branch, branch, id_map, bar)

            logging.info(f"{dst_path.name} saved in {time.perf_counter() - start:.2f}s")

    logging.info("All wells split successfully.")
    return [str(p) for p in out_dir.glob(f"{rec_name}_well???.raw.h5")]

# ----------------------------------------------------------------------
# Main entrypoint
# ----------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: split_maxtwo.py <s3_path_to_maxtwo_rec.raw.h5>")

    s3_path = sys.argv[1]
    s3_base_path = posixpath.dirname(s3_path)  # e.g. s3://bucket/…/original/data

    rec_basename = Path(s3_path).name            # e.g. M06359_D51_…raw.h5
    rec_name     = rec_basename.split(".")[0]    # strip extension

    local_raw   = Path(LOCAL_WORKDIR) / rec_basename
    local_split = Path(LOCAL_WORKDIR) / SPLIT_SUBDIR
    log_file    = local_split / "maxtwo_rec_split.log"   # need a s3 location to store the logs 
    local_split.mkdir(parents=True, exist_ok=True)

    setup_logging(str(log_file))
    setup_hdf5_plugin()

    if not wr.does_object_exist(s3_path):
        logging.error(f"Source file not found on S3: {s3_path}")
        sys.exit(1)

    # download_s3_with_retry(s3_path, str(local_raw))

    split_files = split_maxtwo_by_well(
        local_h5 = str(local_raw),
        rec_name = rec_name,
        out_dir  = str(local_split)
    )
    
    logging.info(f"Split files: {split_files}")
    logging.info("Uploading split files back to S3...")

    # # upload each split file back to …/original/split/<file>
    # dst_prefix = s3_base_path.replace("original/data", "original/split")
    # for f in split_files:
    #     dst = posixpath.join(posixpath.dirname(dst_prefix), Path(f).name)
    #     upload_s3_with_retry(f, dst)

    # logging.info("Done.")
