from kubernetes import client, config
import os
import logging
import re

DEFAULT_S3_BUCKET = "s3://braingeneers/ephys/"
PARAMETER_BUCKET = "s3://braingeneers/services/mqtt_job_listener/params"
SPLITTER_IMAGE = "braingeneers/maxtwo_splitter:v0.40"
SPLITTER_RESOURCES = {
    "cpu": "6",
    "memory": "48Gi",
    "ephemeral-storage": "400Gi",
    "nvidia.com/gpu": "0",
}

class Kube:
    def __init__(self, job_name: str, job_info: dict, namespace='braingeneers'):
        config.load_kube_config()
        self.batch_v1 = client.BatchV1Api()
        self.namespace = namespace
        self.job_name = job_name
        self.job_info = job_info
        if "file_path" in job_info:
            s3_path = job_info["file_path"]
        else:
            if job_info["uuid"].startswith("s3"):
                s3_path = os.path.join(job_info["uuid"],
                                       "original/data",
                                       job_info["experiment"])
            else:
                s3_path = os.path.join(DEFAULT_S3_BUCKET,
                                       job_info["uuid"],
                                       "original/data",
                                       job_info["experiment"])
        if "derived/" in s3_path:
            s3_path = s3_path.replace("original/data/","")
        if "params" in job_info:
            params_path = f"{PARAMETER_BUCKET}/{job_info['params']}"
            logging.info(f"Creating a job for {s3_path} with parameters {params_path}")
            self.args = f"{job_info['args']} {s3_path} {params_path}"
        else:
            logging.info(f"Creating a job for {s3_path} without parameters")
            self.args = f"{job_info['args']} {s3_path}"
        
        self.splitter_source = self._splitter_source_path(s3_path)
        self.use_maxtwo_splitter = bool(self.job_info.get("with_maxtwo_splitter"))
        self.resources = {"cpu": str(self.job_info["cpu_request"]),
                          "memory": str(self.job_info["memory_request"]) + "Gi",
                          "ephemeral-storage": str(self.job_info["disk_request"]) + "Gi",
                          "nvidia.com/gpu": str(self.job_info["GPU"])}

    def _splitter_source_path(self, s3_path: str) -> str:
        source = s3_path
        if "/original/split/" in source:
            source = source.replace("/original/split/", "/original/data/")

        basename = os.path.basename(source)
        dirname = os.path.dirname(source)
        base = re.sub(r"_well\d{3}(?=\.raw\.h5$|\.h5$)", "", basename)
        if base != basename:
            source = os.path.join(dirname, base)

        if source.startswith("s3://braingeneersdev/"):
            source = source.replace("s3://braingeneersdev/", "s3://braingeneers/", 1)

        return source

    def create_job_object(self):
        env_vars = [
            client.V1EnvVar(name="PYTHONUNBUFFERED", value='true'),
            # client.V1EnvVar(name="ENDPOINT_URL", value="http://rook-ceph-rgw-nautiluss3.rook"),
            # client.V1EnvVar(name="S3_ENDPOINT", value="rook-ceph-rgw-nautiluss3.rook")],
            client.V1EnvVar(name="ENDPOINT_URL", value="https://s3.braingeneers.gi.ucsc.edu"),  # use external url to avoid 403 error
            client.V1EnvVar(name="S3_ENDPOINT", value="s3.braingeneers.gi.ucsc.edu")
        ]
        volume_mounts = [
            client.V1VolumeMount(name="prp-s3-credentials", mount_path="/root/.aws/credentials",
                                 sub_path="credentials"),
            client.V1VolumeMount(name="ephemeral", mount_path="/data")
        ]
        container = client.V1Container(
            name="container",
            image=self.job_info["image"],
            image_pull_policy="Always",
            command=["stdbuf", "-i0", "-o0", "-e0", "/usr/bin/time", "-v", "bash", "-c"],
            args=[self.args],
            resources=client.V1ResourceRequirements(
                requests=self.resources,
                limits=self.resources
            ),
            env=env_vars,
            volume_mounts=volume_mounts)
        init_container = None
        if self.use_maxtwo_splitter:
            init_container = client.V1Container(
                name="maxtwo-splitter",
                image=SPLITTER_IMAGE,
                image_pull_policy="Always",
                command=["stdbuf", "-i0", "-o0", "-e0", "/usr/bin/time", "-v", "bash", "-c"],
                args=[f"./start_splitter.sh {self.splitter_source}"],
                resources=client.V1ResourceRequirements(
                    requests=SPLITTER_RESOURCES,
                    limits=SPLITTER_RESOURCES
                ),
                env=env_vars,
                volume_mounts=volume_mounts)
        if "whitelist_nodes" in self.job_info:
            affinity = client.V1Affinity(
                node_affinity=client.V1NodeAffinity(
                    required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                        node_selector_terms=[client.V1NodeSelectorTerm(match_expressions=[
                            client.V1NodeSelectorRequirement(key="kubernetes.io/hostname", operator="In",
                                                             values=self.job_info["whitelist_nodes"]),
                        ])])))
        else:
            affinity = None
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={'name': 'simple-job'}),
            spec=client.V1PodSpec(restart_policy='Never', volumes=[
                client.V1Volume(name="prp-s3-credentials",
                                secret=client.V1SecretVolumeSource(secret_name="prp-s3-credentials")),
                client.V1Volume(name="ephemeral", empty_dir={})],
                                  affinity=affinity,
                                  init_containers=[init_container] if init_container else None,
                                  containers=[container]))
        job = client.V1Job(
            api_version='batch/v1',
            kind='Job',
            metadata=client.V1ObjectMeta(name=self.job_name),
            spec=client.V1JobSpec(backoff_limit=2, template=template))
        return job

    def check_job_exist(self):
        pod_list = self.batch_v1.list_namespaced_job(
            namespace=self.namespace).items
        job_name_list = set([item.metadata.name for item in pod_list])
        if self.job_name in job_name_list:
            return True
        else:
            return False

    def create_job(self):
        resp = self.batch_v1.create_namespaced_job(
            body=self.create_job_object(),
            namespace=self.namespace)
        return resp

    def check_job_status(self):
        if self.check_job_exist():
            job_status = self.batch_v1.read_namespaced_job_status(
                name=self.job_name, namespace=self.namespace).status
            if job_status.active:
                return True
        return False

    def delete_job(self):
        resp = self.batch_v1.delete_namespaced_job(
            name=self.job_name,
            namespace=self.namespace,
            body=client.V1DeleteOptions(
                propagation_policy='Foreground',
                grace_period_seconds=0))
