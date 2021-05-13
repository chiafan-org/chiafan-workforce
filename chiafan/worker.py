import logging
import time
import threading
from pathlib import Path
from .job import PlottingJob


class PlottingWorker(object):
    def __init__(self, name: str,
                 workspace: Path, destination: Path,
                 is_mock: bool = False):
        self.name = name
        self.workspace = workspace
        self.plotting_space = Path(self.workspace, name)
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
            s3_bucket = '',
            farm_key = farm_key,
            pool_key = pool_key,
            log_dir = Path('/tmp'),
            is_mock = self.is_mock)
        logging.info(f'Spawn job {self.current_job.job_name}')
