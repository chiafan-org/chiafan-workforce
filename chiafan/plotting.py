from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from .utils import format_age


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
            'plotting_space': self.plotting_space,
            'destination': self.destination,
            'stage': self.running.name if self.running is not RunningState.RUNNING else self.stage.name,
            'progress': f'{self.progress:.2f} %',
        }


class PlottingProcess(object):
    def __init__(self, plotting_space: Path, destination: Path, is_mock: bool = False):
        self.plotting_space = plotting_space
        self.destination = destination
        self.is_mock = is_mock
        self.starting_time = datetime.now()
        self.all_stages = [Stage.FORWARD, Stage.BACKWARD, Stage.COMPRESSION, Stage.WRITE_CHECKPOINT, Stage.END]
        self.running_state = RunningState.RUNNING
        self.popen = None
        

    def inspect(self):
        if self.is_mock:
            return self._inspect_mock()
        return None


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
