import time
import logging
import threading
from pathlib import Path
from .job import PlottingJob, JobState
from .worker import PlottingWorker
from .utils import check_chiabox_docker_status

class ChiaManager(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChiaManager, cls).__new__(cls)
            cls._instance.workers = []
            cls._instance.past_jobs_status = []
            cls._instance.farm_key = ''
            cls._instance.pool_key = ''
            cls._instance.thread = None
        return cls._instance


    def set_farm_key(self, farm_key):
        self.farm_key = farm_key


    def set_pool_key(self, pool_key):
        self.pool_key = pool_key


    def add_worker(self, workspace: Path, destination: Path, is_mock: bool = False):
        index = len(self.workers) + 1
        self.workers.append(PlottingWorker(
            name = f'worker{index}',
            workspace = workspace,
            destination = destination,
            is_mock = is_mock))



    def run(self):
        self.thread = threading.Thread(target = ChiaManager._run,
                                       args = (self,))
        self.thread.start()


    def _run(self):
        if not ChiaManager._wait_for_chiabox_docker(20):
            raise RuntimeError('Chiabox docker failed to start')

        while True:
            for worker in self.workers:
                if worker.current_job is None:
                    worker.spawn_job(self.farm_key, self.pool_key)
            for worker in self.workers:
                if worker.current_job.state is not JobState.ONGOING:
                    if worker.current_job.state is JobState.FAIL:
                        job_name = worker.current_job.job_name
                        error_message = worker.current_job.error_message
                        logging.error(f'Job {job_name} failed due to "{error_message}"')
                    worker.current_job.thread.join()
                    self.past_jobs_status.append(worker.current_job.inspect())
                    worker.current_job = None
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
        result = []
        for worker in self.workers:
            if worker.current_job is not None:
                result.append(worker.current_job.inspect())
        for job_status in self.past_jobs_status:
            result.append(job_status)
        return result


    def inspect_workers(self):
        return [worker.inspect() for worker in self.workers]
