import time
import logging
from pathlib import Path
from .job import PlottingJob, JobState
from .utils import check_chiabox_docker_status

class ChiaManager(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChiaManager, cls).__new__(cls)
            cls._instance.active_jobs = []
            cls._instance.past_jobs_status = []
            cls._instance.job_index = 0
        return cls._instance


    def run(self,
            workspace: Path, farm_key: str = '', pool_key: str = '',
            total_jobs: int = None,
            concurrent: int = 1):

        if not PlottingProcess._wait_for_chiabox_docker(20):
            raise RuntimeError('Chiabox docker failed to start')

        while True:
            while len(self.active_jobs) < concurrent:
                self.job_index += 1
                self.active_jobs.append(PlottingJob(
                    job_name = f'Job {self.job_index}',
                    # TODO(breakds): Use reserved directory
                    plotting_space = Path(workspace, f'{self.job_index}'),
                    destination = Path(workspace, 'plots'),
                    log_dir = '/tmp',
                    farm_key = farm_key,
                    pool_key = pool_key))

            remaining = []
            for job in self.active_jobs:
                if job.state is not JobState.ONGOING:
                    # TODO(breakd): Check join success
                    job.thread.join()
                    self.past_jobs_status.append(job.inspect)
                else:
                    remaining.append(job)
            self.active_jobs = remaining

            time.sleep(1.6)

    @staticmethod
    def _wait_for_chiabox_docker(num_trials: int = 20):
        """Returns true if the chiabox docker is up.
        Otherwise it will keep trying checking the status of the
        chiabox docker for num_trials times.
        Returns False if the docker container is not up after that
        many trials.
        """
        for i in range(num_trials):
            if i != 0:
                time.sleep(1)                
            docker_status = check_chiabox_docker_status()
            if docker_status == 'running':
                return True
            logging.info(f'{i + 1}/{num_trials} trials, chiabox docker container status = {docker_status}')
        logging.error(f'chiabox docker failed to start')
        return False            


    def get_status(self):
        return [job.inspect()]
