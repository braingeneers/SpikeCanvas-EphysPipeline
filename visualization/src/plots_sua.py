import numpy as np
import matplotlib.pyplot as plt
import logging
import utils

class PlotSUA:
    def __init__(self, spike_data, title=None, isi_range=50, save_to=None):
        self.title = title
        self.save_to = save_to
        self.isi_range = isi_range
        self.fs = spike_data["fs"]
        if isinstance(spike_data["train"], dict):
            self.train = [t/self.fs for _, t in spike_data["train"].items()]
        elif isinstance(spike_data["train"], list):
            self.train = [t/self.fs for t in spike_data["train"]]
        else:
            raise ValueError("spike_data['train'] should be a list or dict")
        logging.info(f"Plotting individual figures for {len(self.train)} units")
        
        self.rec_len = np.max([t[-1] for t in self.train])
        print(f"Recording length: {self.rec_len}")

        self.neuron_data = spike_data["neuron_data"]
    
    def plot_sua(self):
        """
        create subplots and plot features for each unit
        """
        for k, data in self.neuron_data.items():
            cluster = data["cluster_id"]
            npos = data["neighbor_positions"]
            ntemp = data["neighbor_templates"]
            print(f"Unit {cluster} has {len(npos)} neighbors and {len(ntemp)} templates")
            isi = np.diff(self.train[k])*1000    # neuron_data key is the index of the train
            logging.info(f"Plotting the No. {k} unit (cluster {cluster}) with {len(self.train[k])} spikes")

            # create a figure 
            fig = plt.figure(figsize=(9.3, 12.4), constrained_layout=True)
            plt.suptitle(f"{self.title} Unit {cluster}", fontsize=16)  # for some reason this line doesn't work for nrp
            gs = fig.add_gridspec(4, 3)
            ax0 = fig.add_subplot(gs[:2, :2]) # footprint
            ax1 = fig.add_subplot(gs[0, 2])   # spike waveform
            ax2 = fig.add_subplot(gs[1, 2])   # ACG
            ax3 = fig.add_subplot(gs[2, :2])  # firing rate
            ax4 = fig.add_subplot(gs[2, 2])   # ISI
            ax5 = fig.add_subplot(gs[3, :2])  # amplitude
            ax6 = fig.add_subplot(gs[3, 2])   # amp hist

            # 1. plot footprint
            ax0 = PlotSUA.plot_inset(axs=ax0, temp_pos=npos, templates=ntemp)
            ax0.set_title(f"Unit Footprint")
            ax0.set_xlabel(u"\u03bcm", fontsize=11)
            ax0.set_ylabel(u"\u03bcm", fontsize=11)

            # 2. plot spike waveform
            if "waveforms" in data:
                raw_waveform = data["waveforms"]
                xx = np.arange(raw_waveform.shape[1]) / self.fs * 1000
                ax1.plot(xx, raw_waveform.T, color='k', alpha=0.2)
                ax1.plot(xx, np.mean(raw_waveform, axis=0), color='r', linewidth=2)
                ax1.set_title(f"Waveform", fontsize=11)
            else:
                waveform = data["template"]
                xx = np.arange(len(waveform)) / self.fs * 1000
                ax1.plot(xx, waveform, color='r', linewidth=2)
                ax1.set_title(f"Template", fontsize=11)
            ax1.set_xlabel("Time (ms)", fontsize=11)
            ax1.set_ylabel("Voltage (uV)", fontsize=11)

            # 3. plot ACG
            bt = utils.sparse_train([self.train[k]])
            acg, lags = utils.ccg(bt[0], bt[0], ccg_win=[-50, 50])
            ind = np.where(lags == 0)[0][0]
            acg[ind] = 0   # remove the value for lag=0
            ax2.set_title(f"Auto-correlogram", fontsize=11)
            ax2.bar(lags, acg, width=1)
            ax2.set_xlim([-50, 50])
            # set ticks
            ax2.set_xticks(np.arange(-50, 51, 25))
            ax2.set_xlabel("Time (ms)", fontsize=11)
            ax2.set_ylabel("Counts", fontsize=11)

            # 4. plot firing rate
            bins, fr = utils.get_population_fr([self.train[k]], bin_size=0.05)
            ax3.set_title(f"Firing rate", fontsize=11)
            ax3.plot(bins[:-1], fr, linewidth=2)
            ax3.set_xlim([0, self.rec_len])
            ax3.set_xlabel("Time (s)", fontsize=11)
            ax3.set_ylabel("Firing rate (Hz)", fontsize=11)
            ax3.spines['right'].set_visible(False)
            ax3.spines['top'].set_visible(False)

            # 5. plot isi in range [0, 50] ms
            ax4.hist(isi, bins=np.arange(self.isi_range), density=True)
            ax4.set_title(f"ISI distribution [0, 50] ms", fontsize=11)
            ax4.set_xlabel("ISI (ms)", fontsize=11)
            ax4.set_ylabel("Probability", fontsize=11)
            ax4.set_xlim([0, self.isi_range])

            # 6. plot amplitude scatter
            amplitude_values = data["amplitudes"]
            ax5.set_title(f"Amplitude", fontsize=11)
            ax5.scatter(self.train[k], amplitude_values, s=25)
            ax5.set_xlabel("Time (s)", fontsize=11)
            ax5.set_ylabel("Amplitude (uV)", fontsize=11)
            ax5.set_xlim([0, self.rec_len])
            ax5.spines['right'].set_visible(False)
            ax5.spines['top'].set_visible(False)

            # 7. amplitude histogram
            ax6.set_title(f"Amplitude histogram", fontsize=11)
            ax6.hist(amplitude_values, bins=20, orientation='horizontal')
            ax6.set_yticks([])
            ax6.set_xlabel("Counts", fontsize=11)

            for ax in [ax0, ax1, ax2, ax3, ax4, ax5, ax6]:
                ax.tick_params(axis='both', which='major', labelsize=11)
                ax.tick_params(axis='both', which='minor', labelsize=11)

            # plt.tight_layout()
            if self.save_to is not None:
                plt.savefig(f"{self.save_to}/sua_{self.title}_unit_{cluster}.png", dpi=300)
                plt.close()
                logging.info(f"Done plotting SUA figures, saved to {self.save_to}")
    
    @staticmethod
    def plot_inset(axs, temp_pos, templates, nelec=2, ylim_margin=0, pitch=17.5):
        assert len(temp_pos) == len(templates), "Input length must be the same!"
        # find the max template
        if isinstance(templates, list):
            templates = np.asarray(templates)
        amp = np.max(templates, axis=1) - np.min(templates, axis=1)
        max_amp_index = np.argmax(amp)
        position = temp_pos[max_amp_index]
        axs.scatter(position[0], position[1], linewidth=10, alpha=0.2, color='grey')
        axs.text(position[0], position[1], str(position), color="g", fontsize=12)
        # set same scaling to the insets
        ylim_min = min(templates[max_amp_index])
        ylim_max = max(templates[max_amp_index])
        # choose channels that are close to the center channel
        for i in range(len(temp_pos)):
            chn_pos = temp_pos[i]
            if position[0] - nelec * pitch <= chn_pos[0] <= position[0] + nelec * pitch \
                    and position[1] - nelec * pitch <= chn_pos[1] <= position[1] + nelec * pitch:
                axin = axs.inset_axes([chn_pos[0]-5, chn_pos[1]-5, 15, 20], transform=axs.transData)
                axin.plot(templates[i], color='k', linewidth=2, alpha=0.7)
                axin.set_ylim([ylim_min - ylim_margin, ylim_max + ylim_margin])
                axin.set_axis_off()
        axs.set_xlim(position[0]-1.5*nelec*pitch, position[0]+1.5*nelec*pitch)
        axs.set_ylim(position[1]-1.5*nelec*pitch, position[1]+1.5*nelec*pitch)
        axs.invert_yaxis()
        return axs
        





# inner_grid = gs[0, 3:].subgridspec(ncols=2, nrows=1, 
#                                    width_ratios=[4, 1], 
#                                    wspace=0)
# (ax20, ax21) = inner_grid.subplots()  # amplitude + histogram