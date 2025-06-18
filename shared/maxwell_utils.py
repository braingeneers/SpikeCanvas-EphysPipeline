"""
Unified Maxwell data handling utilities.
Consolidates well detection and data reading across all components.
"""
import h5py
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class MaxwellDataReader:
    """Unified Maxwell data reader with well detection."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._well_cache = None
    
    def get_available_wells(self) -> List[str]:
        """Get all available wells in the recording."""
        if self._well_cache is not None:
            return self._well_cache
            
        with h5py.File(self.file_path, 'r') as dataset:
            if 'mapping' in dataset.keys():
                # Legacy MaxOne format - no wells
                self._well_cache = []
            else:
                # MaxTwo format - find wells
                rec_group = dataset['recordings']['rec0000']
                well_keys = [key for key in rec_group.keys() if key.startswith('well')]
                well_keys.sort()  # Consistent ordering
                self._well_cache = well_keys
                
        logger.info(f"Found wells in {self.file_path}: {self._well_cache}")
        return self._well_cache
    
    def get_gain(self, well_index: int = 0) -> float:
        """Get gain value, with dynamic well detection."""
        with h5py.File(self.file_path, 'r') as dataset:
            if 'mapping' in dataset.keys():
                # Legacy MaxOne format
                return dataset['settings']['lsb'][0] * 1e6
            else:
                # MaxTwo format
                wells = self.get_available_wells()
                if not wells:
                    raise KeyError("No well groups found in the recording")
                
                if well_index >= len(wells):
                    raise IndexError(f"Well index {well_index} out of range. Available wells: {wells}")
                
                well_key = wells[well_index]
                logger.info(f"Using well: {well_key}")
                return dataset['recordings']['rec0000'][well_key]['settings']['lsb'][0] * 1e6
    
    def get_mapping(self, well_index: int = 0) -> Dict[str, np.ndarray]:
        """Get electrode mapping, with dynamic well detection."""
        with h5py.File(self.file_path, 'r') as dataset:
            if 'version' in dataset.keys() and 'mxw_version' in dataset.keys():
                # MaxTwo format
                wells = self.get_available_wells()
                if not wells:
                    raise KeyError("No well groups found in the recording")
                    
                if well_index >= len(wells):
                    raise IndexError(f"Well index {well_index} out of range. Available wells: {wells}")
                
                well_key = wells[well_index]
                logger.info(f"Using well: {well_key}")
                mapping = dataset['recordings']['rec0000'][well_key]['settings']['mapping']
            else:
                # Legacy MaxOne format
                mapping = dataset['mapping']
            
            return {
                'pos_x': np.array(mapping['x']),
                'pos_y': np.array(mapping['y']),
                'channel': np.array(mapping['channel']),
                'electrode': np.array(mapping['electrode'])
            }
    
    def get_data_format(self) -> str:
        """Determine the data format."""
        with h5py.File(self.file_path, 'r') as dataset:
            if 'mapping' in dataset.keys():
                return "MaxOne"
            else:
                return "MaxTwo"

# Convenience functions for backward compatibility
def read_maxwell_gain(h5_file: str, well_index: int = 0) -> float:
    """Read Maxwell gain with dynamic well detection."""
    reader = MaxwellDataReader(h5_file)
    return reader.get_gain(well_index)

def read_maxwell_mapping(h5_file: str, well_index: int = 0) -> Dict[str, np.ndarray]:
    """Read Maxwell mapping with dynamic well detection."""
    reader = MaxwellDataReader(h5_file)
    return reader.get_mapping(well_index)
