from kubernetes import client, config
import os

class Kube:
    def __init__(self, job_name: str, dataset_prefix: str):
        config.load_kube_config()
        self.batch_v1 = client.BatchV1Api()
        self.namespace = os.getenv('NRP_NAMESPACE', 'braingeneers')
        self.job_name = job_name
        run_script = os.getenv('KILOSORT_RUN_ARGS', './run.sh')
        self.args = f"{run_script} {dataset_prefix}"

    def create_job_object(self):
        image = os.getenv('KILOSORT_IMAGE', 'surygeng/kilosort_docker:v0.2')
        endpoint_url = os.getenv('ENDPOINT_URL', 'https://s3.braingeneers.gi.ucsc.edu')
        s3_endpoint = os.getenv('S3_ENDPOINT', 's3.braingeneers.gi.ucsc.edu')
        req_cpu = os.getenv('JOB_CPU_REQUEST', '16')
        req_mem = os.getenv('JOB_MEM_REQUEST', '32Gi')
        req_ephem = os.getenv('JOB_EPHEMERAL_REQUEST', '300Gi')
        lim_cpu = os.getenv('JOB_CPU_LIMIT', req_cpu)
        lim_mem = os.getenv('JOB_MEM_LIMIT', req_mem)
        lim_ephem = os.getenv('JOB_EPHEMERAL_LIMIT', '400Gi')
        lim_gpu = int(os.getenv('JOB_GPU_LIMIT', '1'))
        container = client.V1Container(
            name="container",
            image=image,
            image_pull_policy="Always",
            command=["stdbuf", "-i0", "-o0", "-e0", "/usr/bin/time", "-v", "bash", "-c"],
            args=[self.args],
            resources=client.V1ResourceRequirements(
                requests={"cpu": req_cpu, "memory": req_mem, "ephemeral-storage": req_ephem},
                limits={"cpu": lim_cpu, "memory": lim_mem, "ephemeral-storage": lim_ephem, "nvidia.com/gpu": lim_gpu}),
            env=[client.V1EnvVar(name="PYTHONUNBUFFERED", value='true'),
                 client.V1EnvVar(name="ENDPOINT_URL", value=endpoint_url),
                 client.V1EnvVar(name="S3_ENDPOINT", value=s3_endpoint)],
            volume_mounts=[client.V1VolumeMount(name="prp-s3-credentials", mount_path="/root/.aws/credentials",
                                                sub_path="credentials")])
        affinity = client.V1Affinity(
            node_affinity=client.V1NodeAffinity(
                required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                    node_selector_terms=[client.V1NodeSelectorTerm(match_expressions=[client.V1NodeSelectorRequirement(
                        key="nvidia.com/gpu.product", operator="In", values=["NVIDIA-GeForce-GTX-1080-Ti"]),
                        client.V1NodeSelectorRequirement(key="kubernetes.io/hostname", operator="NotIn",
                                                         values=["None"]),
                        client.V1NodeSelectorRequirement(key="feature.node.kubernetes.io/cpu-cpuid.AVX", operator="In",
                                                         values=["true"])])])))
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
            spec=client.V1JobSpec(backoff_limit=0, template=template))
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
        return self.batch_v1

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
