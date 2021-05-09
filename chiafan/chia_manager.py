from .plotting import PlottingProcess

class ChiaManager(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChiaManager, cls).__new__(cls)
            cls._instance.plotting_processes = []
        return cls._instance


    def create_plot(self):
        self.plotting_processes.append(PlottingProcess('/a/b/c', '/d/e/f', is_mock = True))


    def get_status(self):
        return [process.inspect() for process in self.plotting_processes]
