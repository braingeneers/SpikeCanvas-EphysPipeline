import posixpath
import os
from collections import namedtuple
from braingeneers.analysis import SpikeData


class ExpData(SpikeData):
    def __init__(self, spike_trains, groups: dict, days: list):
        if isinstance(spike_trains, dict):
            self._train_dict = spike_trains
            self.spike_data = Bunch.bunchify(spike_trains)
        else:
            self.spike_data = spike_trains

        if groups is not None and isinstance(groups, dict):
            assert "patient" and "control" in groups, f"keyError, \
                keys must be 'patient' and 'control' \
                for groups dictionary"
            pc = namedtuple("line", ["patient", "control"])
            self.pairs = []
            patient = groups["patient"]
            control = groups["control"]
            pairs = []
            for i in range(len(patient)):
                new_pair = pc(patient[i], control[i])
                if new_pair not in pairs:
                    self.pairs.append(new_pair)
        if days is not None:
            self.days = days

    # def get_firing_rate(self):


class Bunch(dict):
    def __init__(self, *args, **kwargs):
        super(Bunch, self).__init__(*args, **kwargs)
        self.__dict__ = self

    @classmethod
    def bunchify(cls, data):
        """
        Construct from nested dictionaries.
        """
        if not isinstance(data, dict):
            return data
        else:
            return cls({key: cls.bunchify(data[key]) for key in data})

