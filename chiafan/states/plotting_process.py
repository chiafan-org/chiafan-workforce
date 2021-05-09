from datetime import datetime
from pathlib import Path
from .plotting_summary import PlottingSummary


class PlottingProcess(object):
    def __init__(self, plotting_space: Path, destination: Path, is_mock: bool = False):
        self.plotting_space = plotting_space
        self.destination = destination
        self.is_mock = is_mock
        self.starting_time = datetime.now()
        

    def status(self):
        return {
            'seconds_elapsed': (datetime.now() - self.starting_time).seconds
        }
