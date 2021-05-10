import time
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from .utils import format_age, check_chiabox_docker_status, inspect_log



class Stage(Enum):
    FORWARD = 1
    BACKWARD = 2
    COMPRESSION = 3
    WRITE_CHECKPOINT = 4
    END = 16


class RunningState(Enum):
    RUNNING = 1
    FAIL = 2
    SUCCESS = 3


class PlottingStatus(object):
    def __init__(self, plotting_space: Path, destination: Path,
                 time_elapsed: timedelta,
                 stage: Stage,
                 progress: float,
                 running: RunningState):
        self.plotting_space = plotting_space
        self.destination = destination
        self.time_elapsed = time_elapsed
        self.stage = stage
        self.progress = progress
        self.running = running


    def to_payload(self):
        return {
            'age': format_age(self.time_elapsed),
            'plotting_space': str(self.plotting_space),
            'destination': str(self.destination),
            'stage': (self.running.name
                      if self.running is not RunningState.RUNNING
                      else self.stage.name),
            'progress': f'{self.progress:.2f} %',
        }


class PlottingProcess(object):
    def __init__(self, plotting_space: Path, destination: Path, log_dir: Path = Path('/tmp'),
                 is_mock: bool = False):
        self.plotting_space = plotting_space
        self.destination = destination
        self.is_mock = is_mock
        self.starting_time = datetime.now()
        self.all_stages = [Stage.FORWARD,
                           Stage.BACKWARD,
                           Stage.COMPRESSION,
                           Stage.WRITE_CHECKPOINT,
                           Stage.END]
        self.running_state = RunningState.RUNNING
        self.log_path = Path(
            log_dir, self.starting_time.strftime('chiafan_plotting_%Y%m%d_%H_%M_%S.log'))
        if not is_mock:
            self.popen = self._create_plotting_job()


    def _create_plotting_job(self):
        if not PlottingProcess._wait_for_chiabox_docker(20):
            return None
        self.log_file = open(self.log_path, 'w')
        proc = subprocess.Popen(['chiaplot1'], stdout = self.log_file, stderr = self.log_file)
        logging.info(f'Started plotting job, log at {self.log_path}')
        return proc


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


    def inspect(self):
        if self.is_mock:
            return self._inspect_mock()
        time_elapsed = datetime.now() - self.starting_time
        stage_id, progress = inspect_log(self.log_path)
        if stage_id == 5:
            self.running_state = RunningState.SUCCESS
        return PlottingStatus(plotting_space = self.plotting_space,
                              destination = self.destination,
                              time_elapsed = time_elapsed,
                              stage = self.all_stages[stage_id - 1],
                              running = self.running_state,
                              progress = progress)


    def _inspect_mock(self):
        time_elapsed = datetime.now() - self.starting_time
        stage = None
        if time_elapsed > timedelta(seconds = 60):
            self.running_state = RunningState.SUCCESS
            stage = Stage.END
        elif time_elapsed > timedelta(seconds = 50):
            self.running_state = RunningState.RUNNING
            stage = Stage.WRITE_CHECKPOINT
        elif time_elapsed > timedelta(seconds = 40):
            self.running_state = RunningState.RUNNING
            stage = Stage.COMPRESSION
        elif time_elapsed > timedelta(seconds = 20):
            self.running_state = RunningState.RUNNING
            stage = Stage.BACKWARD
        elif time_elapsed > timedelta(seconds = 0):
            self.running_state = RunningState.RUNNING
            stage = Stage.FORWARD
        progress = 100.0
        if self.running_state == RunningState.RUNNING:
            progress = time_elapsed.total_seconds() / 60.0 * 100
        return PlottingStatus(plotting_space = self.plotting_space,
                              destination = self.destination,
                              time_elapsed = time_elapsed,
                              stage = stage,
                              running = self.running_state,
                              progress = progress)
