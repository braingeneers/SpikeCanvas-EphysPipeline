from kubernetes import client, config
import os
import logging

try:
    from k8s_config import load_s3_settings
    _s3 = load_s3_settings()
    DEFAULT_S3_BUCKET = _s3["root"]
except Exception:
    _fallback_bucket = os.getenv("S3_BUCKET", "braingeneers")
    _fallback_prefix = os.getenv("S3_PREFIX", "ephys")
    DEFAULT_S3_BUCKET = f"s3://{_fallback_bucket}/{_fallback_prefix.rstrip('/')}/"

# Parameter bucket can be overridden; defaults under service bucket or separate var
SERVICE_BUCKET = os.getenv("SERVICE_BUCKET", "s3://braingeneers/services/mqtt_job_listener")
PARAMETER_BUCKET = os.getenv("PARAMETER_BUCKET", f"{SERVICE_BUCKET}/params")

class Kube:
    def __init__(self, job_name: str, job_info: dict, namespace=os.getenv('NRP_NAMESPACE', 'braingeneers')):
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
        
        self.resources = {"cpu": str(self.job_info["cpu_request"]),
                          "memory": str(self.job_info["memory_request"]) + "Gi",
                          "ephemeral-storage": str(self.job_info["disk_request"]) + "Gi",
                          "nvidia.com/gpu": str(self.job_info["GPU"])}

    def create_job_object(self):
        # Build environment variables to inject into algorithm container
        # This propagates S3 config from listener deployment to algorithm pods
        job_env = [
            client.V1EnvVar(name="PYTHONUNBUFFERED", value='true'),
        ]
        
        # S3 configuration (bucket/prefix)
        try:
            if '_s3' in globals():
                job_env.extend([
                    client.V1EnvVar(name="S3_BUCKET", value=_s3["bucket"]),
                    client.V1EnvVar(name="S3_PREFIX", value=_s3["prefix"])
                ])
        except Exception:
            pass
        
        # Also check direct env vars as fallback
        if os.getenv("S3_BUCKET"):
            job_env.append(client.V1EnvVar(name="S3_BUCKET", value=os.getenv("S3_BUCKET")))
        if os.getenv("S3_PREFIX"):
            job_env.append(client.V1EnvVar(name="S3_PREFIX", value=os.getenv("S3_PREFIX")))
        
        # S3 endpoint configuration (allow override for different providers)
        endpoint_url = os.getenv("ENDPOINT_URL", "https://s3.braingeneers.gi.ucsc.edu")
        s3_endpoint = os.getenv("S3_ENDPOINT", "s3.braingeneers.gi.ucsc.edu")
        job_env.extend([
            client.V1EnvVar(name="ENDPOINT_URL", value=endpoint_url),
            client.V1EnvVar(name="S3_ENDPOINT", value=s3_endpoint)
        ])
        
        # AWS credentials (if set in listener environment, propagate to jobs)
        for aws_var in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", 
                        "AWS_PROFILE"]:
            val = os.getenv(aws_var)
            if val:
                job_env.append(client.V1EnvVar(name=aws_var, value=val))
        
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
            env=job_env,
            volume_mounts=[client.V1VolumeMount(name="prp-s3-credentials", mount_path="/root/.aws/credentials",
                                                sub_path="credentials"),
                           client.V1VolumeMount(name="ephemeral", mount_path="/root")])
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
