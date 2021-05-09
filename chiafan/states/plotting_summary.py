from pathlib import Path

class PlottingSummary(object):
    def __init__(self, plotting_space: Path, destination: Path, progress: float):
        self.plotting_space = plotting_space
        self.destination = destination
        self.progress = progress


    def __repr__(self) -> str:
        return f'Plotting, ({self.plotting_space} -> {self.destination}), {self.progress} %'
