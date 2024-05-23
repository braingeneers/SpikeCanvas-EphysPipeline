import numpy as np
import utils as utils
import sys
import logging
import posixpath
import os
import plots as plots
import plots_sua as plots_sua
import braingeneers.utils.s3wrangler as wr
import shutil


# download data from s3. This can be phy, manual curated or auto curated data
# create a local folder for plots
# zip and upload the plots to s3, name after the downloaded file 

LOG_FILE_NAME = "viz.log"

def setup_logging(log_file):
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(message)s',
                        handlers=[logging.FileHandler(log_file, mode="a"),
                                  stream_handler])


def curation_to_spike_data(cur_file):
    if cur_file.endswith("zip") and "curated" in cur_file:
        logging.info(f"Reading manual curated data from {cur_file}")
        fs, spike_train, neuron_data = utils.read_phy_files(cur_file)
        trains = [np.array(t)*fs for t in spike_train]
    elif cur_file.endswith("_acqm.zip"):
        logging.info(f"Reading auto curated data from {cur_file}")
        train, neuron_data, _, fs = utils.load_curation(cur_file)
        trains = [np.array(t)*fs for t in train]
    else:
        logging.error(f"File format not recognized: {cur_file}")
        sys.exit(1)
    spike_data = {"fs": fs, "train": trains, "neuron_data": neuron_data}
    return spike_data


if __name__ == "__main__":
    # test data: s3://braingeneers/ephys/2024-04-09-e-JLS-midbrain-chimpmisc/derived/kilosort2/Trace_20240405_14_55_30_ch22152-chimp2_phy_curatedJLS.zip
    data_path = sys.argv[1]
    if not wr.does_object_exist(data_path):
        logging.exception(f"Data doesn't exist! Check the path: {data_path}")
        sys.exit(1)

    cur_file = data_path.split("/")[-1]
    figure_name = cur_file.replace(".zip", "")

    # download file from s3
    current_folder = os.getcwd()
    data_subfolder = "/data"
    figure_subfolder = "/figure"
    data_folder = current_folder + data_subfolder
    figure_folder = current_folder + figure_subfolder

    if not os.path.isdir(data_folder):
        os.makedirs(data_folder)
    if not os.path.isdir(figure_folder):
        os.makedirs(figure_folder)

    log_file = os.path.join(figure_folder, LOG_FILE_NAME)
    setup_logging(log_file)
    
    curation_local_path = posixpath.join(data_folder, cur_file) 
    logging.info(f"Start downloading curation file to local {curation_local_path} ...")
    wr.download(data_path, curation_local_path)
    logging.info("Done!")

    spike_data_new = curation_to_spike_data(curation_local_path)

    pe = plots.PlotlyEphys(spike_data_new, title=figure_name)
    overview_figure = pe.plot_html_page()
    overview_figure.write_html(f"{figure_folder}/{figure_name}_overview.html")
    ## also save the output parameter so later I can add/delete things on the figure
    overview_figure.write_json(f"{figure_folder}/{figure_name}_overview.json")
    ## save individual figures as well (for each unit)
    sua_folder = os.path.join(figure_folder, "sua")
    if not os.path.isdir(sua_folder):
        os.makedirs(sua_folder)
    psua = plots_sua.PlotSUA(spike_data_new, title=figure_name, save_to=sua_folder)
    psua.plot_sua()

    logging.info("All plots are saved.")

    # package exract_dir and upload to s3
    figure_file = shutil.make_archive(posixpath.join(data_folder, "figure"), format="zip", root_dir=figure_folder)
    upload_path = data_path.replace(".zip", "_figure.zip")
    logging.info(f"Uploading data from {figure_file} to {upload_path} ...")
    wr.upload(local_file=figure_file, path=upload_path)
    logging.info(f"Figure plotting is done! Result saved to {upload_path}")
