# MaxWell Ephys Pipeline Dashboard - Complete Usage Guide

## Overview

The MaxWell Ephys Pipeline Dashboard is a comprehensive web-based interface for managing electrophysiology data processing workflows. This dashboard provides tools for dataset management, job submission, real-time monitoring, and data visualization for neural recording analysis.

## Quick Start

1. **Launch the Dashboard**
   ```bash
   cd /path/to/MaxWell_Dashboard/src
   python app.py
   ```
   
2. **Access the Interface**
   - Open your web browser and navigate to: `http://127.0.0.1:8050/`
   - The dashboard runs on port 8050 and is accessible from any device on the network

3. **Navigate Between Pages**
   - Use the navigation links at the top of each page to switch between different modules

## Dashboard Modules

### 🏠 Home Page
**Purpose**: Central hub with overview and quick access to documentation

**Features**:
- Dashboard overview and welcome information
- Quick links to all available modules
- System status indicators
- Recent activity summary

### 🔧 Job Center (Data Processing Center)
**Purpose**: Primary interface for submitting and managing data processing jobs

#### Dataset Selection
1. **Select Dataset by UUID**
   - Use the dropdown menu to select from available datasets
   - Each dataset is identified by its unique UUID
   - Selected dataset metadata will display automatically

2. **Filter Datasets**
   - Use the keyword filter to narrow down the dataset list
   - Enter relevant terms (experiment name, date, etc.)
   - Filtered results update the dropdown in real-time

3. **View Metadata**
   - Dataset metadata displays in the read-only text area
   - Includes experiment details, recording parameters, and file information

#### Job Configuration
1. **Batch Processing Options**
   - **Batch Process with Standard Pipeline**: Runs the complete ephys pipeline
   - **Clear All Selected**: Resets all selections and starts over

2. **Recording Selection**
   - **Select All**: Choose all available recordings in the dataset
   - **Reset**: Clear current recording selections
   - **Individual Selection**: Check specific recordings from the list

3. **Available Job Types**
   - ✅ **Ephys Pipeline**: Complete pipeline (Kilosort2 + Auto-Curation + Visualization)
   - 📊 **Auto-Curation**: Quality metrics and unit validation
   - 📈 **Visualization**: Generate plots and visual summaries
   - 🔗 **Functional Connectivity**: Network analysis and connectivity metrics
   - 📡 **Local Field Potential Subbands**: LFP frequency analysis

#### Parameter Management
1. **Set Custom Parameters**
   - Input parameter file names and values
   - Parameters are job-specific and validate automatically
   - Save parameter sets for reuse

2. **Load Existing Parameters**
   - Select a job type to load default parameters
   - View current parameter settings in the display area
   - Reload or modify parameters as needed

3. **Parameter Table Management**
   - Add configured parameters to the parameter table
   - View all active parameter sets
   - Remove or modify parameter configurations

#### Job Submission
1. **Add to Job Table**
   - Review job configuration before submission
   - Add configured jobs to the execution queue
   - Verify all parameters and selections

2. **Export and Start Job**
   - Submit jobs to the processing cluster
   - Jobs are queued and executed automatically
   - Receive confirmation of successful submission

### 📊 Status Monitor
**Purpose**: Real-time monitoring of job execution and system status

#### Job Status Tracking
1. **Refresh Status**
   - Click "Refresh" to update job status information
   - View current state of all submitted jobs
   - Monitor progress and completion status

2. **Status Indicators**
   - **Running**: Job is currently executing
   - **Succeeded**: Job completed successfully
   - **Failed**: Job encountered an error
   - **Pending**: Job is queued for execution

3. **Detailed Information**
   - View job logs and error messages
   - Check resource utilization
   - Monitor execution time and progress

### 📈 Analytics & Visualization
**Purpose**: Interactive data exploration and analysis tools

#### Data Exploration
1. **Dataset Loading**
   - Select processed datasets for analysis
   - Load spike sorting results and quality metrics
   - Choose specific recordings or time periods

2. **Interactive Plots**
   - **Electrode Map**: Spatial distribution of recording sites
   - **Raster Plots**: Spike timing visualization
   - **ISI Histograms**: Inter-spike interval analysis
   - **Template Waveforms**: Unit spike shapes
   - **Firing Rate Distributions**: Population activity analysis

3. **Advanced Analytics**
   - **STTC Analysis**: Spike time tiling coefficient for connectivity
   - **Burst Detection**: Identification of burst patterns
   - **Network Connectivity**: Functional connectivity matrices
   - **Quality Metrics**: Unit isolation and stability measures

#### Visualization Controls
1. **Parameter Adjustment**
   - STTC delta timing window (default: 20ms)
   - STTC threshold (default: 0.35)
   - Firing rate coefficient (default: 10)

2. **Unit Selection**
   - Filter by quality metrics
   - Select individual units for detailed analysis
   - Compare multiple units simultaneously

3. **Time Range Selection**
   - Choose specific time periods for analysis
   - Zoom and pan through long recordings
   - Synchronize multiple plot views

### 📊 Analytics Gallery
**Purpose**: Pre-configured analysis templates and visualization galleries

#### Template Analyses
1. **Standard Metrics**
   - Population firing rate analysis
   - Network connectivity summaries
   - Quality control reports

2. **Custom Workflows**
   - Save frequently used analysis configurations
   - Share analysis templates with team members
   - Load and modify existing workflows

## Best Practices

### Data Management
- **Organize Datasets**: Use consistent naming conventions for experiments
- **Metadata Completion**: Ensure all dataset metadata is complete and accurate
- **Regular Backups**: Processed results are automatically backed up to S3

### Job Submission
- **Resource Planning**: Consider computational requirements for large datasets
- **Parameter Validation**: Test parameters on small datasets before large-scale processing
- **Queue Management**: Monitor job queue to avoid resource conflicts

### Quality Control
- **Review Results**: Always review auto-curation results before final analysis
- **Manual Curation**: Use manual curation tools for critical datasets
- **Documentation**: Document any manual interventions or parameter changes

## Troubleshooting

### Common Issues

#### Job Submission Problems
- **Error**: "Dataset not found"
  - **Solution**: Verify UUID spelling and dataset availability
  - **Check**: Ensure dataset is uploaded and accessible

- **Error**: "Parameter validation failed"
  - **Solution**: Review parameter values and formats
  - **Check**: Ensure all required parameters are provided

#### Processing Failures
- **Error**: "Insufficient resources"
  - **Solution**: Reduce dataset size or adjust resource requests
  - **Check**: Monitor cluster resource availability

- **Error**: "Spike sorting failed"
  - **Solution**: Check data quality and preprocessing parameters
  - **Check**: Review raw data for artifacts or issues

#### Visualization Issues
- **Error**: "No data to display"
  - **Solution**: Ensure processing completed successfully
  - **Check**: Verify output files exist and are accessible

- **Error**: "Plot rendering timeout"
  - **Solution**: Reduce data size or time range
  - **Check**: Browser compatibility and performance

### Getting Help

1. **Check System Status**: Verify all services are running normally
2. **Review Logs**: Check job logs for specific error messages
3. **Contact Support**: Reach out to the Braingeneers team for assistance
4. **Documentation**: Refer to the detailed README files for specific modules

## System Requirements

### Browser Compatibility
- **Recommended**: Chrome, Firefox, Safari (latest versions)
- **Minimum**: Any modern browser with JavaScript enabled
- **Note**: Internet Explorer is not supported

### Network Requirements
- **Local Access**: Dashboard accessible at `localhost:8050`
- **Network Access**: Available on local network at host IP
- **Internet**: Required for S3 data access and updates

### Performance Recommendations
- **RAM**: Minimum 8GB for large dataset visualization
- **CPU**: Multi-core processor recommended for responsive interface
- **Storage**: Sufficient local storage for temporary files

## Security & Access

### Authentication
- Currently operates without authentication for local use
- Can be configured with username/password authentication if needed
- Contact administrators for multi-user deployments

### Data Privacy
- All data processing follows institutional guidelines
- Results are stored securely in encrypted S3 buckets
- No personal data is transmitted outside the secure environment

---

## Support Information

**Project**: Braingeneers @ UCSC  
**Maintainer**: Maxwell Ephys Pipeline Team  
**Documentation**: See individual module README files  
**Updates**: Dashboard is actively maintained and updated regularly  

For technical support or feature requests, please contact the development team or submit issues through the appropriate channels.
