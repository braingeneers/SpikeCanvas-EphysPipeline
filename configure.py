#!/usr/bin/env python3
"""
Interactive Configuration Setup for SpikeCanvas
This script helps users create their .env configuration file through
an interactive command-line interface.
"""

import os
import sys
from pathlib import Path


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_info(text):
    """Print informational text"""
    print(f"\n[INFO] {text}")


def print_success(text):
    """Print a success message"""
    print(f"\n[SUCCESS] {text}")


def print_warning(text):
    """Print a warning message"""
    print(f"\n[WARNING] {text}")


def get_input(prompt, default=None, required=True):
    """Get user input with optional default value"""
    if default:
        prompt_text = f"{prompt} [{default}]: "
    else:
        prompt_text = f"{prompt}: "
    
    while True:
        value = input(prompt_text).strip()
        
        if value:
            return value
        elif default is not None:
            return default
        elif not required:
            return ""
        else:
            print("This field is required. Please enter a value.")


def get_yes_no(prompt, default="y"):
    """Get yes/no input from user"""
    valid_yes = ["y", "yes"]
    valid_no = ["n", "no"]
    
    default_text = "Y/n" if default.lower() == "y" else "y/N"
    prompt_text = f"{prompt} [{default_text}]: "
    
    while True:
        value = input(prompt_text).strip().lower()
        
        if not value:
            return default.lower() in valid_yes
        elif value in valid_yes:
            return True
        elif value in valid_no:
            return False
        else:
            print("Please enter 'y' or 'n'")


def validate_bucket_name(bucket):
    """Remove s3:// prefix if present"""
    if bucket.startswith("s3://"):
        bucket = bucket[5:]
    return bucket.rstrip("/")


def main():
    """Main configuration function"""
    config = {}
    
    print("\n" + "=" * 70)
    print("  SpikeCanvas - Easy Setup")
    print("=" * 70)
    print("\nThis will help you set up the pipeline in 5 simple steps:")
    print("  1. S3 Storage")
    print("  2. AWS Credentials")
    print("  3. S3 Endpoint")
    print("  4. Service Configuration")
    print("  5. Kubernetes")
    print("\nThis takes about 2 minutes. Ready? Let's go!")
    print()
    
    # Check if .env already exists
    env_path = Path(".env")
    if env_path.exists():
        print_warning("Found existing .env file")
        if not get_yes_no("Do you want to overwrite it?", default="n"):
            print("\nKeeping your existing configuration.")
            return
        
        # Backup existing file
        backup_path = Path(".env.backup")
        env_path.rename(backup_path)
        print(f"Backed up existing .env to .env.backup")
    
    # ==========================================================================
    # S3 Storage Configuration
    # ==========================================================================
    print_header("Step 1: S3 Storage Setup")
    print("\nWhere is your electrophysiology data stored?")
    print("\nThe pipeline organizes data like this:")
    print("   s3://your-bucket/ephys/")
    print("   └── UUID-123/                    (your experiment ID)")
    print("       ├── original/data/           (raw recordings)")
    print("       └── derived/                 (processing results)")
    print("           ├── kilosort2/          (spike sorting)")
    print("           ├── connectivity/       (connectivity analysis)")
    print("           ├── lfp/                (LFP analysis)")
    print("           └── visualization/      (plots & figures)")
    
    bucket = get_input("\nWhat is your S3 bucket name? (just the name, no s3://)")
    config["S3_BUCKET"] = validate_bucket_name(bucket)
    
    print(f"\nUsing bucket: {config['S3_BUCKET']}")
    
    print("\nThe 'prefix' is the root folder for all your ephys data.")
    print("Example: if prefix='ephys', your data structure will be:")
    print(f"  s3://{config['S3_BUCKET']}/ephys/UUID-123/original/data/")
    
    prefix = get_input(
        "\nWhat is the root folder name for ephys data?",
        default="ephys",
        required=False
    )
    config["S3_PREFIX"] = prefix if prefix else "ephys"
    
    print(f"\nYour data structure:")
    print(f"   Raw data:    s3://{config['S3_BUCKET']}/{config['S3_PREFIX']}/UUID/original/data/")
    print(f"   Results:     s3://{config['S3_BUCKET']}/{config['S3_PREFIX']}/UUID/derived/<algorithm>/")
    
    # Skip advanced options for simplicity
    config["S3_INPUT_PREFIX"] = ""
    config["S3_OUTPUT_PREFIX"] = ""
    
    # ==========================================================================
    # AWS Credentials
    # ==========================================================================
    print_header("Step 2: AWS Credentials")
    print("\nYou'll need AWS credentials to access S3 storage.")
    
    config["AWS_ACCESS_KEY_ID"] = get_input(
        "\nAWS Access Key ID"
    )
    config["AWS_SECRET_ACCESS_KEY"] = get_input(
        "AWS Secret Access Key"
    )
    config["AWS_DEFAULT_REGION"] = get_input("AWS Region", default="us-west-2")
    
    print("\nCredentials saved")
    
    # ==========================================================================
    # S3 Endpoint Configuration
    # ==========================================================================
    print_header("Step 3: S3 Endpoint")
    print("\nExamples:")
    print("  • Standard: https://s3.us-west-2.amazonaws.com")
    print("  • Braingeneers: https://s3.braingeneers.gi.ucsc.edu")
    
    config["S3_ENDPOINT_URL"] = get_input(
        "\nS3 Endpoint URL"
    )
    
    # ==========================================================================
    # Service Configuration
    # ==========================================================================
    print_header("Step 4: Service Configuration")
    print("\nThe pipeline stores service data (logs, status files, etc.) in S3.")
    print("We'll automatically set this up for you.")
    
    # Always use standard service paths
    config["SERVICES_PATH"] = f"s3://{config['S3_BUCKET']}/services"
    config["LOGS_PATH"] = f"{config['SERVICES_PATH']}/logs"
    config["STATUS_PATH"] = f"{config['SERVICES_PATH']}/status"
    config["RESULTS_PATH"] = f"{config['SERVICES_PATH']}/results"
    
    print(f"Service data will be stored at: s3://{config['S3_BUCKET']}/services/")
    
    # ==========================================================================
    # Kubernetes Configuration
    # ==========================================================================
    print_header("Step 5: Kubernetes")
    print("\nIf you're using NRP, this should be your NRP namespace.")
    
    namespace = get_input(
        "\nKubernetes namespace",
        default="",
        required=False
    )
    if namespace:
        config["K8S_NAMESPACE"] = namespace
        print(f"Jobs will run in namespace: {namespace}")
    
    # ==========================================================================
    # Summary and Save
    # ==========================================================================
    print_header("Configuration Summary")
    print(f"\n   S3 Bucket:     s3://{config['S3_BUCKET']}/{config['S3_PREFIX']}/")
    print(f"   AWS Region:    {config['AWS_DEFAULT_REGION']}")
    print(f"   Access Key:    {config['AWS_ACCESS_KEY_ID'][:8]}...{config['AWS_ACCESS_KEY_ID'][-4:]}")
    print(f"   Endpoint:      {config['S3_ENDPOINT_URL']}")
    print(f"   Namespace:     {config.get('K8S_NAMESPACE', 'default')}")
    print()
    
    # Ask for confirmation
    if not get_yes_no("\nSave this configuration?", default="y"):
        print("\nConfiguration cancelled. Nothing was saved.")
        return
    
    # Write .env file
    env_content = f"""# SpikeCanvas Configuration
# Generated by configure.py

# ============================================================
# S3 Storage Configuration
# ============================================================
S3_BUCKET={config['S3_BUCKET']}
S3_PREFIX={config['S3_PREFIX']}
S3_INPUT_PREFIX={config['S3_INPUT_PREFIX']}
S3_OUTPUT_PREFIX={config['S3_OUTPUT_PREFIX']}
S3_ENDPOINT_URL={config['S3_ENDPOINT_URL']}

# ============================================================
# AWS Credentials
# ============================================================
AWS_ACCESS_KEY_ID={config['AWS_ACCESS_KEY_ID']}
AWS_SECRET_ACCESS_KEY={config['AWS_SECRET_ACCESS_KEY']}
AWS_DEFAULT_REGION={config['AWS_DEFAULT_REGION']}

# ============================================================
# Service Configuration
# ============================================================
SERVICES_PATH={config['SERVICES_PATH']}
LOGS_PATH={config['LOGS_PATH']}
STATUS_PATH={config['STATUS_PATH']}
RESULTS_PATH={config['RESULTS_PATH']}

# ============================================================
# Kubernetes Configuration
# ============================================================
"""
    
    if "K8S_NAMESPACE" in config:
        env_content += f"K8S_NAMESPACE={config['K8S_NAMESPACE']}\n"
    
    # Write the file
    with open(".env", "w") as f:
        f.write(env_content)
    
    # Set restrictive permissions (owner read/write only)
    os.chmod(".env", 0o600)
    
    print_success("Configuration saved to .env")
    print("\nNext steps:")
    print("  1. Review the .env file if needed")
    print("  2. Start the pipeline with: docker-compose up -d")
    print("\nFor more information, see QUICK_START.md")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)
