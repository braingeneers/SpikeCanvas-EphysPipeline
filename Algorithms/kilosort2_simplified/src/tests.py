import unittest
import utils
import numpy as np

class UtilsTest(unittest.TestCase):
    def test_population_fr(self):
        train_1 = [np.arange(0, 100, 0.01)]
        print(len(train_1[0]))
        bins, fr = utils.get_population_fr(train_1)
        # print(bins.shape)
        self.assertEqual(fr.shape, (1999, ))
        self.assertEqual(bins.shape[0], fr.shape[0]+1)
        train_2 = []
        bins, fr = utils.get_population_fr(train_2)
        self.assertEqual(fr.shape, (0, ))
