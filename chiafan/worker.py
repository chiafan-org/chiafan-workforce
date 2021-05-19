import logging
import time
import threading
from pathlib import Path
from .job import PlottingJob


class PlottingWorker(object):
    def __init__(self, name: str,
                 workspace: Path, destination: Path,
                 forward_concurrency: int = 2,
                 is_mock: bool = False):
        self.name = name
        self.workspace = workspace
        self.plotting_space = Path(self.workspace, name)
        self.forward_concurrency = forward_concurrency
        self.destination = destination
        self.current_job = None
        self.job_index = 0
        self.is_mock = is_mock


    def spawn_job(self, farm_key: str, pool_key: str):
        self.job_index += 1
        self.current_job = PlottingJob(
            job_name = f'{self.name}.job{self.job_index}',
            plotting_space = self.plotting_space,
            destination = self.destination,
            forward_concurrency = self.forward_concurrency,
            s3_bucket = '',
            farm_key = farm_key,
            pool_key = pool_key,
            log_dir = Path('/tmp'),
            is_mock = self.is_mock)


    def inspect(self):
        return {
            'name': self.name,
            'running': 'NOTHING' if self.current_job is None else self.current_job.job_name,
            'plottingSpace': str(self.plotting_space),
            'destination': str(self.destination),
        }


    def ensure_shutdown(self):
        if self.current_job is None:
            return

        self.current_job.ensure_shutdown()


    def abort_job(self):
        if self.current_job is not None:
            self.current_job.abort()
        self.current_job = None


    def used_cpu_count(self):
        if self.current_job is None:
            return 0
        return self.current_job.used_cpu_count()
