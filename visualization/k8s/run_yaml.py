import yaml
import os
import braingeneers.utils.s3wrangler as wr


def create_visualization_jobs(base_yaml, recordings):
    jobs = []
    for i, recording in enumerate(recordings, 1):
        # Load the base YAML
        with open(base_yaml, 'r') as file:
            job_yaml = yaml.safe_load(file)
        
        # Modify the job name
        job_yaml['metadata']['name'] = f'sjg-viz-{i}'
        
        # Modify the args to use the current recording
        job_yaml['spec']['template']['spec']['containers'][0]['args'] = [
            f'python viz.py {recording}'
        ]
        
        jobs.append(job_yaml)
    
    return jobs

def write_jobs_to_files(jobs, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for i, job in enumerate(jobs, 1):
        filename = os.path.join(output_dir, f'visualization_job_{i}.yaml')
        with open(filename, 'w') as file:
            yaml.dump(job, file)


if __name__ == "__main__":
    # List of your 32 recordings
    uuid = "2025-05-09-e-JLS-3D-PL-comp-DREADD-DCZ"
    # all_original = wr.list_objects(f"s3://braingeneers/ephys/{uuid}/original/data/")
    # print(len(all_original))
    # all_derived = wr.list_objects(f"s3://braingeneers/ephys/{uuid}/derived/autocuration/")
    s3_prefix = f"s3://braingeneers/ephys/{uuid}/derived/autocuration/"
    zip_files = [
    "Trace_20250429_12_50_06_chP002381_PL_badconfig_params_jesus_acqm.zip",
    "Trace_20250429_12_50_06_chP002381_PL_badconfig_params_params_low_ISI_acqm.zip",
    "Trace_20250429_13_08_22_P002462_3D_params_jesus_acqm.zip",
    "Trace_20250429_13_08_22_P002462_3D_params_params_low_ISI_acqm.zip",
    "Trace_20250429_13_31_32_chP002381_PL_params_jesus_acqm.zip",
    "Trace_20250429_13_31_32_chP002381_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250429_13_49_24_chP002471_PL_params_jesus_acqm.zip",
    "Trace_20250429_13_49_24_chP002471_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250430_13_27_19_chP002462_3D_params_jesus_acqm.zip",
    "Trace_20250430_13_27_19_chP002462_3D_params_params_low_ISI_acqm.zip",
    "Trace_20250430_13_33_23_chP002381_PL_params_jesus_acqm.zip",
    "Trace_20250430_13_33_23_chP002381_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250430_14_58_28_chP002381_PL_params_jesus_acqm.zip",
    "Trace_20250430_14_58_28_chP002381_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250430_14_59_47_chP002471_PL_params_jesus_acqm.zip",
    "Trace_20250430_14_59_47_chP002471_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250501_13_25_38_chP002381_PL_params_jesus_acqm.zip",
    "Trace_20250501_13_25_38_chP002381_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250501_13_52_44_chP002471_PL_params_jesus_acqm.zip",
    "Trace_20250501_13_52_44_chP002471_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250501_14_00_39_chP002381_PL_params_jesus_acqm.zip",
    "Trace_20250501_14_00_39_chP002381_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250501_14_08_21_chP002462_3D_params_jesus_acqm.zip",
    "Trace_20250501_14_08_21_chP002462_3D_params_params_low_ISI_acqm.zip",
    "Trace_20250502_13_58_14_chP002462_3D_params_jesus_acqm.zip",
    "Trace_20250502_13_58_14_chP002462_3D_params_params_low_ISI_acqm.zip",
    "Trace_20250502_17_04_09_chP002381_PL_params_jesus_acqm.zip",
    "Trace_20250502_17_04_09_chP002381_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250502_17_20_18_chP002471_PL_params_jesus_acqm.zip",
    "Trace_20250502_17_20_18_chP002471_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250505_16_52_48_chP002471_PL_params_jesus_acqm.zip",
    "Trace_20250505_16_52_48_chP002471_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250505_16_55_47_chP002381_PL_params_jesus_acqm.zip",
    "Trace_20250505_16_55_47_chP002381_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250505_17_04_48_chP002462_3D_params_jesus_acqm.zip",
    "Trace_20250505_17_04_48_chP002462_3D_params_params_low_ISI_acqm.zip",
    "Trace_20250506_11_48_37_chP002462_3D_params_jesus_acqm.zip",
    "Trace_20250506_11_48_37_chP002462_3D_params_params_low_ISI_acqm.zip",
    "Trace_20250506_12_21_04_chP002741_PL_params_jesus_acqm.zip",
    "Trace_20250506_12_21_04_chP002741_PL_params_params_low_ISI_acqm.zip",
    "Trace_20250508_10_34_13_chP002462_3D_Baseline_params_jesus_acqm.zip",
    "Trace_20250508_10_34_13_chP002462_3D_Baseline_params_params_low_ISI_acqm.zip",
    "Trace_20250508_10_46_56_chP002381_PL_baseline_params_jesus_acqm.zip",
    "Trace_20250508_10_46_56_chP002381_PL_baseline_params_params_low_ISI_acqm.zip",
    "Trace_20250508_11_01_17_P002471_PL_baseline_params_jesus_acqm.zip",
    "Trace_20250508_11_01_17_P002471_PL_baseline_params_params_low_ISI_acqm.zip",
    "Trace_20250508_11_13_08_chP002462_3D_DCZ_params_jesus_acqm.zip",
    "Trace_20250508_11_13_08_chP002462_3D_DCZ_params_params_low_ISI_acqm.zip",
    "Trace_20250508_11_29_58_chP002471_PL_DCZ_params_jesus_acqm.zip",
    "Trace_20250508_11_29_58_chP002471_PL_DCZ_params_params_low_ISI_acqm.zip",
    "Trace_20250508_11_40_57_chP002471_PL_washout2x_params_jesus_acqm.zip",
    "Trace_20250508_11_40_57_chP002471_PL_washout2x_params_params_low_ISI_acqm.zip",
    "Trace_20250508_12_18_27_chP002462_3D_washout-2x_params_jesus_acqm.zip",
    "Trace_20250508_12_18_27_chP002462_3D_washout-2x_params_params_low_ISI_acqm.zip",
    "Trace_20250508_15_07_43_chP002462_3D_washout-4x_params_jesus_acqm.zip",
    "Trace_20250508_15_07_43_chP002462_3D_washout-4x_params_params_low_ISI_acqm.zip",
    "Trace_20250509_11_12_17_chP002462_3D_newconfig_params_jesus_acqm.zip",
    "Trace_20250509_11_12_17_chP002462_3D_newconfig_params_params_low_ISI_acqm.zip",
    "Trace_20250509_11_35_42_chP002471_PL-newconfig_params_jesus_acqm.zip",
    "Trace_20250509_11_35_42_chP002471_PL-newconfig_params_params_low_ISI_acqm.zip",
    "Trace_20250509_11_53_56_chP002471_PL-oldConfig_params_jesus_acqm.zip",
    "Trace_20250509_11_53_56_chP002471_PL-oldConfig_params_params_low_ISI_acqm.zip",
    "Trace_20250509_12_15_51_chP002381_PL_newconfig_params_jesus_acqm.zip",
    "Trace_20250509_12_15_51_chP002381_PL_newconfig_params_params_low_ISI_acqm.zip"
]
    all_derived = [f"{s3_prefix}{f}" for f in zip_files]

    # phys = [
    #     f for f in all_derived if f.endswith("phy.zip")
    # ]
    # print(len(phys))

    recordings = [
        f for f in all_derived if f.endswith("acqm.zip")
    ]
    print(len(recordings))

    # Create the jobs
    jobs = create_visualization_jobs('run_viz.yaml', recordings)

    # Write the jobs to individual YAML files
    write_jobs_to_files(jobs, 'visualization_jobs_autocuration')

    print(f"{len(jobs)} visualization job YAML files have been created in the 'visualization_jobs_autocuraitn' directory.")
