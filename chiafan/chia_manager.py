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
            cls._instance.shutting_down = False
            cls._instance.workers = []
            cls._instance.past_jobs_status = []
            cls._instance.farm_key = ''
            cls._instance.pool_key = ''
            cls._instance.thread = None
            cls._instance.draining = False
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


    def drain(self):
        self.draining = True
        

    def run(self):
        if self.shutting_down:
            return
        if self.thread is None:
            self.thread = threading.Thread(target = ChiaManager._run,
                                           args = (self,))
            self.thread.start()
        else:
            self.draining = False


    def _run(self):
        if not ChiaManager._wait_for_chiabox_docker(20):
            raise RuntimeError('Chiabox docker failed to start')

        while True:
            if self.shutting_down:
                for worker in self.workers:
                    worker.ensure_shutdown()
                break
            for worker in self.workers:
                if worker.current_job is None and not self.draining:
                    worker.spawn_job(self.farm_key, self.pool_key)
            for worker in self.workers:
                if worker.current_job is None:
                    # Note that this only happens in draining mode
                    continue
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


    def inspect(self):
        pipeline = 'stopped'
        if self.thread is None:
            pipeline = 'stopped'
        elif self.draining:
            pipeline = 'draining'
            idle_worker_count = 0
            for worker in self.workers:
                if worker.current_job is None:
                    idle_worker_count += 1
            if idle_worker_count == len(self.workers):
                pipeline = 'stopped'
        else:
            pipeline = 'working'
        return {
            'pipeline': pipeline
        }


    def ensure_shutdown(self):
        self.shutting_down = True
        if self.thread is None:
            return
        self.thread.join()
