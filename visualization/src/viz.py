import numpy as np
import utils as utils
import sys
import logging
import posixpath
import os


# download data from s3. This can be phy, manual curated or auto curated data
# create a local folder for plots
# zip and upload the plots to s3, name after the downloaded file 


def setup_logging(log_file):
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(message)s',
                        handlers=[logging.FileHandler(log_file, mode="a"),
                                  stream_handler])







if __name__ == "__main__":
    data_path = sys.argv[1]
    s3_base_path, phy_path = parse_uuid(data_path=data_path)
    print(f"s3 path: {data_path}")  # original recording s3 full path
    print(f"s3 base: {s3_base_path}")
    print(f"phy path: {phy_path}")

    # download file from s3
    current_folder = os.getcwd()
    subfolder = "/data"
    base_folder = current_folder + subfolder

    if not os.path.isdir(base_folder):
        os.mkdir(base_folder)
    print(base_folder)
    extract_dir = base_folder + "/kilosort_result"
    kilosort_local_path = posixpath.join(base_folder, "kilosort_result.zip")

    for p in [phy_path, data_path]:
        try:
            assert wr.does_object_exist(p)
        except AssertionError as err:
            logging.exception(f"Data doesn't exist! {p}")
            raise err

    logging.info("Start downloading kilosort result ...")
    wr.download(phy_path, kilosort_local_path)
    logging.info("Done!")

    shutil.unpack_archive(kilosort_local_path, extract_dir, "zip")

    logging.info("Start downloading raw data ...")
    experiment = "rec.raw.h5"
    wr.download(data_path, posixpath.join(base_folder, experiment))
    logging.info("Done")
