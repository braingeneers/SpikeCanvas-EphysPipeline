# to read manual curation result as phy files and convert to auto curation format for running connectivity analysis
from braingeneers import analysis
import numpy as np

file = "elliott_chip21769_2.zip"

spike_data = analysis.read_phy_files(file)
trains = spike_data.train
print(len(trains))
print(len(spike_data.neuron_data[0]))
structured_data = {"train": {c: trains[c] for c in range(spike_data.N)},
                      "neuron_data": spike_data.neuron_data[0],
                      "fs": 20000}
np.savez("elliott_chip21769_2_manual_curation_auto_format.npz", **structured_data)

# load the auto curation format data
data = np.load("elliott_chip21769_2_manual_curation_auto_format.npz", allow_pickle=True)
print("load data")
train = data["train"]
neuron_data = data["neuron_data"]
fs = data["fs"]
print(train)
print(neuron_data)
print(fs)