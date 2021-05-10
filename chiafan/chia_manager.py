from pathlib import Path
from .plotting import PlottingProcess

class ChiaManager(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChiaManager, cls).__new__(cls)
            cls._instance.plotting_processes = []
        return cls._instance


    def create_plot(self, plotting_space: str, destination: str, log_dir: str):
        self.plotting_processes.append(PlottingProcess(
            plotting_space = Path(plotting_space),
            destination = Path(destination),
            log_dir = Path(log_dir)))


    def get_status(self):
        return [process.inspect() for process in self.plotting_processes]
