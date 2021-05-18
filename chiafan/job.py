import io
import time
import random
import signal
from pathlib import Path
import subprocess
import logging
from datetime import datetime, timedelta
import re
import threading
from enum import Enum
from .utils import format_age


STAGE_START_PATTERN = re.compile('^Starting phase (\d)/.*')

STAGE_END_PATTERN = re.compile('^Time for phase (\d) = (.*) seconds.*')

# Renamed final file from "/plots/2/plot-k32-2021-05-13-22-35-f0ec4ccbca548f6a5df44c7ac99882576f1a7145980b197a918b129c6e8be39e.plot.2.tmp" to "/plots/2/plot-k32-2021-05-13-22-35-f0ec4ccbca548f6a5df44c7ac99882576f1a7145980b197a918b129c6e8be39e.plot"
COMPLETE_PATTERN = re.compile('.*Renamed final file from.*to.*"(.*)".*')


class Stage(Enum):
    INITIALIZATION = 1
    FORWARD = 2
    BACKWARD = 3
    COMPRESSION = 4
    WRITE_CHECKPOINT = 5
    S3_MIGRATION = 6
    END = 7

    @staticmethod
    def from_stage_id(stage_id: int):
        if stage_id == 1:
            return Stage.FORWARD
        elif stage_id == 2:
            return Stage.BACKWARD
        elif stage_id == 3:
            return Stage.COMPRESSION
        elif stage_id == 4:
            return Stage.WRITE_CHECKPOINT
        return Stage.END
        

class JobState(Enum):
    ONGOING = 1
    FAIL = 2
    SUCCESS = 3


class StageDetail(object):
    def __init__(self, stage: Stage, time_consumption: timedelta):
        self.stage = stage
        self.time_consumption = time_consumption


    def to_payload(self):
        return {
            'stage': self.stage.name,
            'time_consumption': format_age(self.time_consumption),
        }


class JobStatus(object):
    def __init__(self,
                 job_name: str = '',
                 time_elapsed: timedelta = None,
                 stage: Stage = None,
                 state: JobState = None,
                 stage_details: StageDetail = [],
                 progress: float = None):
        self.job_name = job_name
        self.time_elapsed = time_elapsed
        self.stage = stage
        self.stage_details = stage_details
        self.progress = progress
        self.state = state


    def to_payload(self):
        return {
            'name': self.job_name,
            'age': format_age(self.time_elapsed),
            'stage': (self.state.name
                      if self.state is not JobState.ONGOING
                      else self.stage.name),
            'stageDetails': [ x.to_payload() for x in self.stage_details],
            'progress': f'{self.progress:.2f} %',
        }


class PlottingJob(object):
    def __init__(self, job_name: str,
                 plotting_space: Path, destination: Path,
                 s3_bucket: str,
                 log_dir: Path,
                 forward_concurrency: int = 2,
                 farm_key: str = '',
                 pool_key: str = '',
                 is_mock = False):
        self.job_name = job_name
        self.plotting_space = plotting_space
        self.destination = destination
        self.forward_concurrency = forward_concurrency
        self.farm_key = farm_key
        self.pool_key = pool_key
        self.s3_bucket = s3_bucket
        self.is_mock = is_mock

        self.starting_time = datetime.now()
        self.stop_time = None
        self.log_path = Path(
            log_dir,
            self.starting_time.strftime(f'chiafan_plotting_{self.job_name}_%Y%m%d_%H_%M_%S.log'))

        self.state = JobState.ONGOING
        self.error_message = ''
        self.stage = Stage.INITIALIZATION
        self.stage_details = []
        self.progress = 0.0

        self.proc = None
        self.thread = threading.Thread(target = PlottingJob.run,
                                       args = (self,))
        self.thread.start()
        logging.info(f'Spawn job {self.job_name}, {self.plotting_space} -> {self.destination}')

        self.shutting_down = False

    def inspect(self):
        ref_time = self.stop_time or datetime.now()
        return JobStatus(
            job_name = self.job_name,
            time_elapsed = ref_time - self.starting_time,
            stage = self.stage,
            stage_details = self.stage_details,
            state = self.state,
            progress = self.progress)


    def run(self):
        if self.farm_key == '':
            self.state = JobState.FAIL
            self.error_message = 'Missing farmer key'
            self.stop_time = datetime.now()
            return

        if self.pool_key == '':
            self.state = JobState.FAIL
            self.error_message = 'Missing pool key'
            self.stop_time = datetime.now()            
            return
        
        # Ensure directory exists
        # TODO(breakds): Make this more general
        if self.is_mock:
            self.plotting_space.mkdir(parents = True, exist_ok = True)
            self.destination.mkdir(parents = True, exist_ok = True)
        else:
            try:
                subprocess.check_output(['docker', 'exec', 'chiabox',
                                         'mkdir', '-p', f'{self.plotting_space}'])
                subprocess.check_output(['docker', 'exec', 'chiabox',
                                         'mkdir', '-p', f'{self.destination}'])
            except:
                self.state = JobState.FAIL
                self.error_message = f'Cannot ensure directory {self.plotting_space} and {self.destination}'
                

        # Clear the plotting space
        try:
            subprocess.check_output(['rm', '-rf', f'{self.plotting_space}/*'])
        except:
            self.state = JobState.FAIL
            self.error_message = f'Cannot clean up directory {self.plotting_space}/'

        # Start the plotting process
        if self.is_mock:
            self.proc = subprocess.Popen([
                'chiafan-plot-sim',
                # TODO(breakds): generalize the hardcoded path
                '--destination', f'{self.destination}/plot-k32-{random.randint(0, 10000)}.plot',
                '--duration', '60.0'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        else:
            self.proc = subprocess.Popen([
                'docker', 'exec', 'chiabox', 'venv/bin/chia',
                'plots', 'create',
                '-r', f'{plot.forward_concurrency}',
                '-t', f'{self.plotting_space}',
                '-d', f'{self.destination}',
                '-f', f'{self.farm_key}',
                '-p', f'{self.pool_key}',
                '-n', '1',
            ], stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        # Inspect log
        num_lines = 0
        final_plot = None
        with open(self.log_path, 'w') as log_file:
            for line in io.TextIOWrapper(self.proc.stdout, encoding = 'utf-8'):
                num_lines += 1
                self.progress = num_lines / 2624.0 * 98.0

                log_file.write(line)
                # Force flush the log every 10 lines
                if num_lines % 10 == 0:
                    log_file.flush()

                # TODO(breakds): Handle this more gracefully
                if num_lines > 2650:
                    break
                
                # Now update stage if needed.
                m = STAGE_START_PATTERN.match(line)
                if m is not None:
                    stage_id = int(m.groups()[0])
                    self.stage = Stage.from_stage_id(stage_id)
                    continue
                
                m = STAGE_END_PATTERN.match(line)
                if m is not None:
                    stage_id = int(m.groups()[0])
                    used_seconds = float(m.groups()[1])
                    self.stage_details.append(StageDetail(
                        stage = Stage.from_stage_id(stage_id),
                        time_consumption = timedelta(seconds = used_seconds)))
                    continue
                        
                m = COMPLETE_PATTERN.match(line)
                if m is not None:
                    final_plot = m.groups()[0]
                    continue

        # TODO(breakds): Check num_lines = 2624

        # Now make sure the plotting process ends properly
        try:
            self.proc.communicate(timeout = 60)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.state = JobState.FAIL
            self.error_message = 'Cannot terminate the plotting process'
            self.stop_time = datetime.now()            
            return

        if final_plot is None:
            self.state = JobState.FAIL
            self.error_message = 'Could not locate generated plot'
            self.stop_time = datetime.now()            
            return

        logging.info(f'Succesfully done plot with {self.job_name}. Final plot at {final_plot}')

        if self.s3_bucket == '':
            self.stage = Stage.END
            self.state = JobState.SUCCESS
            self.progress = 100.0
            return
            
        # Migrate to S3
        # TODO(breakds): Add monitoring of S3 migration progress
        self.stage = Stage.S3_MIGRATION
        self.progress = 99.0
        self.proc = subprocess.Popen(['aws', 'mv',
                                      f'{self.destination}/{final_plot}',
                                      self.s3_bucket,
                                      '--no-progress', '--storage-class', 'ONEZONE_IA'])
        
        try:
            # With 60MB/s, a plot should finish migration in 1690 seconds
            self.proc.communicate(timeout = 3600)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.state = JobState.FAIL
            self.error_message = 'Cannot terminate the plotting process'
            self.stop_time = datetime.now()            
            return

        self.progress = 100.0
        self.stage = Stage.END
        self.state = JobState.SUCCESS


    def ensure_shutdown(self):
        self.shutting_down = True
        if self.proc is not None:
            self.proc.kill()
            self.state = JobState.FAIL
            self.error_message = 'Cannot terminate the plotting process'
            self.stop_time = datetime.now()            
        self.thread.join()


    def used_cpu_count(self):
        if self.stage in [Stage.INITIALIZATION, Stage.FORWARD]:
            return self.forward_concurrency
        elif self.stage in [Stage.BACKWARD, Stage.COMPRESSION]:
            return 1
        return 0
