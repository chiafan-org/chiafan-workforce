import io
import time
import random
from pathlib import Path
import subprocess
import logging
from datetime import datetime, timedelta
import re
import threading
from enum import Enum
from .utils import format_age


STAGE_START_PATTERN = re.compile('^Starting phase (\d)/.*')

# 2021-05-12T11:48:34.845  chia.plotting.create_plots       : INFO     plot-k32-2021-05-12-04-41-8d9b4ad89a836810e3baf2f74d88417aaa46223b6955d4213edddfba0f2c4f6a.plot
COMPLETE_PATTERN = re.compile('.*INFO.*(plot-k.*\.plot)[^\.].*')


class Stage(Enum):
    INITIALIZATION = 1
    FORWARD = 2
    BACKWARD = 3
    COMPRESSION = 4
    WRITE_CHECKPOINT = 5
    S3_MIGRATION = 6
    END = 7


class JobState(Enum):
    ONGOING = 1
    FAIL = 2
    SUCCESS = 3


class JobStatus(object):
    def __init__(self,
                 job_name: str = '',
                 time_elapsed: timedelta = None,
                 stage: Stage = None,
                 state: JobState = None,
                 progress: float = None):
        self.job_name = job_name
        self.time_elapsed = time_elapsed
        self.stage = stage
        self.progress = progress
        self.state = state


    def to_payload(self):
        return {
            'name': self.job_name,
            'age': format_age(self.time_elapsed),
            'stage': (self.state.name
                      if self.state is not JobState.ONGOING
                      else self.stage.name),
            'progress': f'{self.progress:.2f} %',
        }


class PlottingJob(object):
    def __init__(self, job_name: str,
                 plotting_space: Path, destination: Path, s3_bucket: str,
                 log_dir: Path,
                 farm_key: str = '',
                 pool_key: str = '',
                 is_mock = False):
        self.job_name = job_name
        self.plotting_space = plotting_space
        self.destination = destination
        self.farm_key = farm_key
        self.pool_key = pool_key
        self.s3_bucket = s3_bucket
        self.is_mock = is_mock

        self.starting_time = datetime.now()
        self.stop_time = None
        self.log_path = Path(
            log_dir,
            self.starting_time.strftime('chiafan_plotting_%Y%m%d_%H_%M_%S.log'))

        self.state = JobState.ONGOING
        self.error_message = ''
        self.stage = Stage.INITIALIZATION
        self.progress = 0.0

        self.proc = None
        self.thread = threading.Thread(target = PlottingJob.run,
                                       args = (self,))
        self.thread.start()


    def inspect(self):
        ref_time = self.stop_time or datetime.now()
        return JobStatus(
            job_name = self.job_name,
            time_elapsed = ref_time - self.starting_time,
            stage = self.stage,
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
        self.plotting_space.mkdir(parents = True, exist_ok = True)
        self.destination.mkdir(parents = True, exist_ok = True)

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
                '--template', '/home/breakds/Downloads/20210508_23_12_27.log',
                '--destination', f'{self.destination}/plot-k32-{random.randint(0, 10000)}.plot',
                '--duration', '10.0'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        else:
            self.proc = subprocess.Popen([
                'docker', 'exec', 'chiabox', 'venv/bin/chia',
                'plots', 'create',
                '-t', f'{self.plotting_space}',
                '-d', f'{self.destination}',
                '-f', f'{self.farm_key}',
                '-p', f'{self.pool_key}',
                '-n', '1',
            ], stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        # Inspect log
        num_lines = 0
        final_plot = None
        print(self.log_path)
        with open(self.log_path, 'w') as log_file:
            for line in io.TextIOWrapper(self.proc.stdout, encoding = 'utf-8'):
                num_lines += 1
                self.progress = num_lines / 2630.0 * 98.0
                # Now update stage if needed.
                m = STAGE_START_PATTERN.match(line)
                if m is not None:
                    stage_id = int(m.groups()[0])
                    if stage_id == 1:
                        self.stage = Stage.FORWARD
                    elif stage_id == 2:
                        self.stage = Stage.BACKWARD
                    elif stage_id == 3:
                        self.stage = Stage.COMPRESSION
                    elif stage_id == 4:
                        self.stage = Stage.WRITE_CHECKPOINT
                else:
                    m = COMPLETE_PATTERN.match(line)
                    if m is not None:
                        final_plot = m.groups()[0]

                log_file.write(line)

                # TODO(breakds): Handle this more gracefully
                if num_lines > 2650:
                    break
                
        # TODO(breakds): Check num_lines = 2630

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
