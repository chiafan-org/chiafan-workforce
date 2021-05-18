import os
import time
from datetime import datetime, timedelta
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
            cls._instance.staggering_sec = 600
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


    def set_staggering_sec(self, staggering_sec):
        self.staggering_sec = staggering_sec


    def add_worker(self, workspace: Path, destination: Path,
                   forward_concurrency: int = 2,
                   is_mock: bool = False):
        index = len(self.workers) + 1
        self.workers.append(PlottingWorker(
            name = f'worker{index}',
            workspace = workspace,
            destination = destination,
            forward_concurrency = forward_concurrency,
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
        is_mock = self.workers[0].is_mock
        if not is_mock:
            if not ChiaManager._wait_for_chiabox_docker(20):
                raise RuntimeError('Chiabox docker failed to start')

        while True:
            if self.shutting_down:
                for worker in self.workers:
                    worker.ensure_shutdown()
                break
            # Staggering Handling
            youngest_job_starting_time = datetime(year = 1970, month = 1, day = 1, second = 0)
            for worker in self.workers:
                if worker.current_job is not None:
                    youngest_job_starting_time = max(
                        youngest_job_starting_time, worker.current_job.starting_time)
            can_spawn =  (datetime.now() - youngest_job_starting_time).total_seconds() > self.staggering_sec

            if (not self.draining) and can_spawn:
                # Not check for cpu availability
                available_cpus = os.cpu_count() - self.used_cpu_count()
                for worker in self.workers:
                    if worker.current_job is None and worker.forward_concurrency <= available_cpus:
                        worker.spawn_job(self.farm_key, self.pool_key)
                        # Only start one at one time maximum because of staggering
                        break
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
        num_workers = len(self.workers)
        active_jobs = 0
        for worker in self.workers:
            if worker.current_job is not None:
                active_jobs += 1
        if self.thread is None:
            pipeline = 'stopped'
        elif self.draining:
            pipeline = 'draining'
            if active_jobs == 0:
                pipeline = 'stopped'
        else:
            pipeline = 'working'
        return {
            'pipeline': pipeline,
            'num_workers': num_workers,
            'active_jobs': active_jobs,
            'cpu_count': os.cpu_count(),
            'used_cpu_count': self.used_cpu_count(),
        }


    def used_cpu_count(self):
        count = 0
        for worker in self.workers:
            count += worker.used_cpu_count()
        return count


    def ensure_shutdown(self):
        self.shutting_down = True
        if self.thread is None:
            return
        self.thread.join()
