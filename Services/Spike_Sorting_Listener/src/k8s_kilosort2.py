from kubernetes import client, config
import os
import logging

DEFAULT_S3_BUCKET = "s3://braingeneers/ephys/"
PARAMETER_BUCKET = "s3://braingeneers/services/mqtt_job_listener/params"

class Kube:
    def __init__(self, job_name: str, job_info: dict, namespace='braingeneers'):
        config.load_kube_config()
        self.batch_v1 = client.BatchV1Api()
        self.namespace = namespace
        self.job_name = job_name
        self.job_info = job_info
        self.gpu_resource = self.job_info.get("gpu_resource", "nvidia.com/gpu")
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
        
        self.resources = {"cpu": str(self.job_info["cpu_request"]),
                          "memory": str(self.job_info["memory_request"]) + "Gi",
                          "ephemeral-storage": str(self.job_info["disk_request"]) + "Gi"}
        gpu_count = int(self.job_info.get("GPU", 0))
        if gpu_count:
            self.resources[self.gpu_resource] = str(gpu_count)

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
        init_cfg = self.job_info.get("init_container")
        init_containers = None
        if init_cfg:
            init_resources = {"cpu": str(init_cfg["cpu_request"]),
                              "memory": str(init_cfg["memory_request"]) + "Gi",
                              "ephemeral-storage": str(init_cfg["disk_request"]) + "Gi"}
            init_gpu = int(init_cfg.get("GPU", 0))
            if init_gpu:
                init_resources[self.gpu_resource] = str(init_gpu)
            init_containers = [client.V1Container(
                name=init_cfg.get("name", "init-container"),
                image=init_cfg["image"],
                image_pull_policy=init_cfg.get("image_pull_policy", "Always"),
                command=["stdbuf", "-i0", "-o0", "-e0", "/usr/bin/time", "-v", "bash", "-c"],
                args=[init_cfg["args"]],
                resources=client.V1ResourceRequirements(
                    requests=init_resources,
                    limits=init_resources
                ),
                env=env_vars,
                volume_mounts=volume_mounts)]
        match_expressions = []
        whitelist_nodes = self.job_info.get("whitelist_nodes") or []
        if whitelist_nodes:
            match_expressions.append(client.V1NodeSelectorRequirement(
                key="kubernetes.io/hostname",
                operator="In",
                values=whitelist_nodes
            ))

        gpu_product = self.job_info.get("gpu_product")
        if gpu_product:
            gpu_values = gpu_product if isinstance(gpu_product, list) else [gpu_product]
            match_expressions.append(client.V1NodeSelectorRequirement(
                key="nvidia.com/gpu.product",
                operator="In",
                values=gpu_values
            ))

        cuda_runtime = self.job_info.get("cuda_runtime") or {}
        runtime_major = cuda_runtime.get("major")
        runtime_minor = cuda_runtime.get("minor")
        if runtime_major:
            match_expressions.append(client.V1NodeSelectorRequirement(
                key="nvidia.com/cuda.runtime.major",
                operator="In",
                values=[str(runtime_major)]
            ))
        if runtime_minor:
            match_expressions.append(client.V1NodeSelectorRequirement(
                key="nvidia.com/cuda.runtime.minor",
                operator="In",
                values=[str(runtime_minor)]
            ))

        cuda_driver = self.job_info.get("cuda_driver") or {}
        driver_major = cuda_driver.get("major")
        driver_minor = cuda_driver.get("minor")
        driver_major_op = cuda_driver.get("major_op", "In")
        driver_minor_op = cuda_driver.get("minor_op", "In")
        if driver_major:
            match_expressions.append(client.V1NodeSelectorRequirement(
                key="nvidia.com/cuda.driver.major",
                operator=driver_major_op,
                values=[str(driver_major)]
            ))
        if driver_minor:
            match_expressions.append(client.V1NodeSelectorRequirement(
                key="nvidia.com/cuda.driver.minor",
                operator=driver_minor_op,
                values=[str(driver_minor)]
            ))

        if match_expressions:
            affinity = client.V1Affinity(
                node_affinity=client.V1NodeAffinity(
                    required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                        node_selector_terms=[client.V1NodeSelectorTerm(
                            match_expressions=match_expressions
                        )]
                    )
                )
            )
        else:
            affinity = None
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={'name': 'simple-job'}),
            spec=client.V1PodSpec(restart_policy='Never', volumes=[
                client.V1Volume(name="prp-s3-credentials",
                                secret=client.V1SecretVolumeSource(secret_name="prp-s3-credentials")),
                client.V1Volume(name="ephemeral", empty_dir={})],
                                  affinity=affinity,
                                  init_containers=init_containers,
                                  containers=[container]))
        backoff_limit = self.job_info.get("backoff_limit", 0)
        job = client.V1Job(
            api_version='batch/v1',
            kind='Job',
            metadata=client.V1ObjectMeta(name=self.job_name),
            spec=client.V1JobSpec(backoff_limit=backoff_limit, template=template))
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
