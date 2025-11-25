FROM nvidia/cuda:11.0.3-base-ubuntu20.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y unzip \
    libxt-dev \
    curl \
    git \
    wget \
    build-essential\
    awscli\
    zip\
    time\
    glances\
    gzip\
    openssl

RUN mkdir /install_matlab \
    && curl http://ssd.mathworks.com/supportfiles/downloads/R2019b/Release/9/deployment_files/installer/complete/glnxa64/MATLAB_Runtime_R2019b_Update_9_glnxa64.zip > /install_matlab/MATLAB_Runtime_R2019b_Update_9_glnxa64.zip \
    && cd /install_matlab && unzip MATLAB_Runtime_R2019b_Update_9_glnxa64.zip && ./install -mode silent -agreeToLicense yes && cd / && rm -rf /install_matlab

### Python
# ubuntu20.04 has a default python3.8 which is not compatiable with braingeneers
RUN apt-get install -y python3\
    python3-pip \
    python-is-python3

# python packages \
# RUN python -m pip install --force-reinstall 'git+https://github.com/SpikeInterface/spikeinterface.git'
RUN pip install "spikeinterface==0.98.0"
RUN pip install "numpy==1.24.4" \
    pandas \
    plotly \
    scipy \
    h5py \
    MEArec\
    pynwb \
    deprecation \
    matplotlib 

#########################################
### Compiled kilosort2
COPY matlab/ /project/matlab
COPY src/ /project/src
RUN chmod +x /project/src/run.sh
RUN chmod +x /project/src/run_temp.sh

# setup work directory
RUN mkdir -p /project/SpikeSorting/inter/sorted/kilosort2
WORKDIR /project/src

# PRP setup
ENV ENDPOINT_URL="https://s3.braingeneers.gi.ucsc.edu"
ENV PATH="/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:."

# container name: 
    # ephys_pipeline:v0.1 - data & parameter input