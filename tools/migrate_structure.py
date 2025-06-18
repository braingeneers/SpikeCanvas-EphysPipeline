#!/usr/bin/env python3
"""
Migration script to reorganize the Maxwell Ephys Pipeline project structure.
This script will move files from the current flat structure to the recommended
hierarchical structure with clear separation between services and containers.
"""

import os
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProjectMigrator:
    """Handles migration from current structure to recommended structure."""
    
    def __init__(self, project_root: str, dry_run: bool = True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.backup_dir = self.project_root / "backup_before_migration"
        
    def create_backup(self):
        """Create a backup of the current structure."""
        if not self.dry_run:
            logger.info(f"Creating backup at {self.backup_dir}")
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
            
            # Create backup of critical directories
            critical_dirs = [
                "job_scanner", "Spike_Sorting_Listener", "MaxWell_Dashboard",
                "kilosort2_simplified", "si_curation_docker", "maxtwo_splitter",
                "connectivity", "visualization", "local_field_potential", "shared"
            ]
            
            self.backup_dir.mkdir()
            for dir_name in critical_dirs:
                src = self.project_root / dir_name
                if src.exists():
                    dst = self.backup_dir / dir_name
                    shutil.copytree(src, dst)
                    logger.info(f"Backed up {src} to {dst}")
    
    def create_new_structure(self):
        """Create the new directory structure."""
        new_dirs = [
            # Top level
            "docs",
            
            # Shared utilities (enhance existing)
            "shared/maxwell_utils",
            "shared/kubernetes_utils", 
            "shared/storage",
            "shared/messaging",
            "shared/config",
            
            # Services (long-running)
            "services/mqtt_job_listener/src",
            "services/mqtt_job_listener/k8s",
            "services/job_scanner/src",
            "services/job_scanner/k8s",
            "services/web_dashboard/src",
            "services/web_dashboard/k8s",
            
            # Containers (processing)
            "containers/spike_sorting/src",
            "containers/spike_sorting/k8s",
            "containers/spike_sorting/matlab",
            "containers/curation/src",
            "containers/curation/k8s",
            "containers/splitter/src",
            "containers/splitter/k8s",
            "containers/visualization/src",
            "containers/visualization/k8s",
            "containers/connectivity/src",
            "containers/connectivity/k8s",
            "containers/lfp_analysis/src",
            "containers/lfp_analysis/k8s",
            
            # Infrastructure
            "infrastructure/docker/base",
            "infrastructure/kubernetes/namespaces",
            "infrastructure/kubernetes/rbac",
            "infrastructure/kubernetes/secrets",
            "infrastructure/kubernetes/configmaps",
            "infrastructure/helm/maxwell-pipeline",
            "infrastructure/helm/services",
            "infrastructure/helm/containers",
            
            # Configuration
            "config/environments",
            "config/parameters/spike_sorting",
            "config/parameters/curation", 
            "config/parameters/visualization",
            "config/parameters/connectivity",
            "config/parameters/lfp_analysis",
            "config/jobs/pipeline_configs",
            "config/jobs/templates",
            
            # Tests
            "tests/unit/shared",
            "tests/unit/services", 
            "tests/unit/containers",
            "tests/integration",
            "tests/fixtures",
            
            # Scripts and tools
            "scripts",
            "tools/migration",
            "tools/monitoring",
            "tools/development",
            
            # Data
            "data/schemas",
            "data/samples",
            "data/test_datasets"
        ]
        
        for dir_path in new_dirs:
            full_path = self.project_root / dir_path
            if self.dry_run:
                logger.info(f"[DRY RUN] Would create directory: {full_path}")
            else:
                full_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {full_path}")
    
    def migrate_services(self):
        """Migrate long-running services."""
        service_migrations = [
            # (old_path, new_path, new_name)
            ("Spike_Sorting_Listener", "services/mqtt_job_listener", "MQTT Job Listener"),
            ("job_scanner", "services/job_scanner", "Job Scanner"),
            ("MaxWell_Dashboard", "services/web_dashboard", "Web Dashboard"),
        ]
        
        for old_path, new_path, display_name in service_migrations:
            self._migrate_component(old_path, new_path, display_name, "service")
    
    def migrate_containers(self):
        """Migrate processing containers."""
        container_migrations = [
            ("kilosort2_simplified", "containers/spike_sorting", "Spike Sorting"),
            ("si_curation_docker", "containers/curation", "Curation"),
            ("maxtwo_splitter", "containers/splitter", "Splitter"),
            ("connectivity", "containers/connectivity", "Connectivity"),
            ("visualization", "containers/visualization", "Visualization"),
            ("local_field_potential", "containers/lfp_analysis", "LFP Analysis"),
        ]
        
        for old_path, new_path, display_name in container_migrations:
            self._migrate_component(old_path, new_path, display_name, "container")
    
    def _migrate_component(self, old_path: str, new_path: str, display_name: str, component_type: str):
        """Migrate a single component."""
        old_dir = self.project_root / old_path
        new_dir = self.project_root / new_path
        
        if not old_dir.exists():
            logger.warning(f"Source directory {old_dir} does not exist, skipping")
            return
        
        logger.info(f"Migrating {display_name} from {old_path} to {new_path}")
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would migrate {old_dir} to {new_dir}")
            return
        
        # Create new directory structure
        new_dir.mkdir(parents=True, exist_ok=True)
        
        # Migrate source code
        old_src = old_dir / "src"
        new_src = new_dir / "src"
        if old_src.exists():
            shutil.copytree(old_src, new_src, dirs_exist_ok=True)
            logger.info(f"  Moved src/ directory")
        
        # Migrate Docker files
        old_docker = old_dir / "docker"
        if old_docker.exists():
            dockerfile = old_docker / "Dockerfile"
            if dockerfile.exists():
                shutil.copy2(dockerfile, new_dir / "Dockerfile")
                logger.info(f"  Moved Dockerfile")
        
        # Migrate Kubernetes files
        old_k8s = old_dir / "k8s"
        new_k8s = new_dir / "k8s"
        if old_k8s.exists():
            shutil.copytree(old_k8s, new_k8s, dirs_exist_ok=True)
            logger.info(f"  Moved k8s/ directory")
        
        # Migrate test files
        old_test = old_dir / "test"
        if old_test.exists():
            test_target = self.project_root / "tests" / "unit" / component_type + "s" / new_path.split("/")[-1]
            test_target.mkdir(parents=True, exist_ok=True)
            shutil.copytree(old_test, test_target, dirs_exist_ok=True)
            logger.info(f"  Moved tests to {test_target}")
        
        # Special handling for matlab directory (spike sorting)
        if old_path == "kilosort2_simplified":
            old_matlab = old_dir / "matlab"
            if old_matlab.exists():
                new_matlab = new_dir / "matlab"
                shutil.copytree(old_matlab, new_matlab, dirs_exist_ok=True)
                logger.info(f"  Moved matlab/ directory")
    
    def migrate_shared_utilities(self):
        """Enhance existing shared utilities."""
        logger.info("Organizing shared utilities")
        
        shared_dir = self.project_root / "shared"
        if not shared_dir.exists():
            logger.warning("Shared directory does not exist")
            return
        
        # The shared utilities are already created, just ensure they're organized
        if self.dry_run:
            logger.info("[DRY RUN] Would organize shared utilities into modules")
        else:
            # Create __init__.py files for proper Python packages
            init_files = [
                "shared/__init__.py",
                "shared/maxwell_utils/__init__.py", 
                "shared/kubernetes_utils/__init__.py",
                "shared/storage/__init__.py",
                "shared/messaging/__init__.py",
                "shared/config/__init__.py"
            ]
            
            for init_file in init_files:
                init_path = self.project_root / init_file
                if not init_path.exists():
                    init_path.touch()
                    logger.info(f"Created {init_file}")
    
    def migrate_configuration(self):
        """Migrate and organize configuration files."""
        logger.info("Migrating configuration files")
        
        # Move parameters directory
        old_params = self.project_root / "parameters"
        new_params = self.project_root / "config" / "parameters"
        
        if old_params.exists():
            if self.dry_run:
                logger.info(f"[DRY RUN] Would move {old_params} to {new_params}")
            else:
                new_params.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(old_params, new_params, dirs_exist_ok=True)
                logger.info(f"Moved parameters to {new_params}")
    
    def migrate_infrastructure(self):
        """Migrate infrastructure and deployment files."""
        logger.info("Migrating infrastructure files")
        
        # Move existing docker directory
        old_docker = self.project_root / "docker"
        new_docker = self.project_root / "infrastructure" / "docker"
        
        if old_docker.exists():
            if self.dry_run:
                logger.info(f"[DRY RUN] Would move {old_docker} to {new_docker}")
            else:
                new_docker.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(old_docker, new_docker, dirs_exist_ok=True)
                logger.info(f"Moved docker files to {new_docker}")
        
        # Move k8s directory if it exists
        old_k8s = self.project_root / "k8s"
        new_k8s = self.project_root / "infrastructure" / "kubernetes"
        
        if old_k8s.exists():
            if self.dry_run:
                logger.info(f"[DRY RUN] Would move {old_k8s} to {new_k8s}")
            else:
                shutil.copytree(old_k8s, new_k8s, dirs_exist_ok=True)
                logger.info(f"Moved k8s files to {new_k8s}")
    
    def migrate_scripts(self):
        """Migrate build and deployment scripts."""
        logger.info("Migrating scripts")
        
        scripts_to_move = [
            "build.sh",
            "deploy.sh", 
            "migrate_to_new_structure.py"
        ]
        
        scripts_dir = self.project_root / "scripts"
        if not self.dry_run:
            scripts_dir.mkdir(exist_ok=True)
        
        for script in scripts_to_move:
            old_script = self.project_root / script
            new_script = scripts_dir / script
            
            if old_script.exists():
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would move {script} to scripts/")
                else:
                    shutil.copy2(old_script, new_script)
                    logger.info(f"Moved {script} to scripts/")
    
    def create_new_files(self):
        """Create new configuration and documentation files."""
        if self.dry_run:
            logger.info("[DRY RUN] Would create new configuration and documentation files")
            return
        
        # Create pyproject.toml
        pyproject_content = '''[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "maxwell-ephys-pipeline"
version = "2.0.0"
description = "Maxwell Microelectrode Array Electrophysiology Processing Pipeline"
authors = [
    {name = "Braingeneers Team", email = "info@braingeneers.gi.ucsc.edu"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "numpy>=1.20.0",
    "h5py>=3.0.0",
    "kubernetes>=18.0.0",
    "braingeneers>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=6.0.0",
    "black>=21.0.0",
    "flake8>=3.8.0",
    "mypy>=0.800",
]

[tool.setuptools.packages.find]
where = ["shared"]
include = ["maxwell_utils*", "kubernetes_utils*", "storage*", "messaging*", "config*"]
'''
        
        with open(self.project_root / "pyproject.toml", "w") as f:
            f.write(pyproject_content)
        logger.info("Created pyproject.toml")
        
        # Create .env.example
        env_example = '''# Maxwell Ephys Pipeline Configuration
KUBE_NAMESPACE=braingeneers
JOB_PREFIX=edp-
S3_BUCKET=braingeneers
MQTT_BROKER_HOST=mqtt.braingeneers.gi.ucsc.edu
SLACK_WEBHOOK_URL=your_slack_webhook_url
LOG_LEVEL=INFO
ENVIRONMENT=development
'''
        
        with open(self.project_root / ".env.example", "w") as f:
            f.write(env_example)
        logger.info("Created .env.example")
    
    def cleanup_old_structure(self):
        """Remove old directories after successful migration."""
        if self.dry_run:
            logger.info("[DRY RUN] Would remove old directory structure")
            return
        
        # Only remove if migration was successful
        response = input("Migration completed. Remove old directories? (y/N): ")
        if response.lower() == 'y':
            old_dirs = [
                "Spike_Sorting_Listener", "job_scanner", "MaxWell_Dashboard",
                "kilosort2_simplified", "si_curation_docker", "maxtwo_splitter",
                "connectivity", "visualization", "local_field_potential"
            ]
            
            for old_dir in old_dirs:
                old_path = self.project_root / old_dir
                if old_path.exists():
                    shutil.rmtree(old_path)
                    logger.info(f"Removed old directory: {old_path}")
    
    def run_migration(self):
        """Run the complete migration process."""
        logger.info("Starting project structure migration")
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Dry run: {self.dry_run}")
        
        try:
            # Phase 1: Backup and prepare
            self.create_backup()
            self.create_new_structure()
            
            # Phase 2: Migrate components
            self.migrate_services()
            self.migrate_containers()
            self.migrate_shared_utilities()
            
            # Phase 3: Migrate supporting files
            self.migrate_configuration()
            self.migrate_infrastructure()
            self.migrate_scripts()
            
            # Phase 4: Create new files
            self.create_new_files()
            
            # Phase 5: Cleanup (optional)
            if not self.dry_run:
                self.cleanup_old_structure()
            
            logger.info("Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            if not self.dry_run and self.backup_dir.exists():
                logger.info(f"Backup available at: {self.backup_dir}")
            raise

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate Maxwell Ephys Pipeline to new structure")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--no-dry-run", action="store_true", help="Actually perform migration")
    
    args = parser.parse_args()
    
    migrator = ProjectMigrator(
        project_root=args.project_root,
        dry_run=not args.no_dry_run
    )
    
    migrator.run_migration()

if __name__ == "__main__":
    main()
