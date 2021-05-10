from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import re

STAGE_START_PATTERN = re.compile('^Starting phase (\d)/.*')
STAGE_END_PATTERN = re.compile('^Time for phase (\d)/.*')

def format_age(age: timedelta) -> str:
    hours = age.seconds // 3600
    minutes = (age.seconds % 3600) // 60
    seconds = age.seconds % (3600 * 60)
    if age.days > 0:
        return f'{age.days} days {hours:02d}:{minutes:02d}:{seconds:02d}'
    else:
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def check_chiabox_docker_status():
    output = subprocess.check_output(
        ['docker', 'inspect', '-f', '{{.State.Status}}', 'chiabox'])
    return output.decode('utf-8').strip()


def inspect_log(log_path: Path):
    """Retruns a pair (current_stage_id, progress)

    """
    stage_id = 1
    num_lines = 0
    with open(log_path, 'r') as f:
        for line in f:
            num_lines += 1
            m = STAGE_START_PATTERN.match(line)
            if m is not None:
                print(m.groups())
                stage_id = int(m.groups()[0])
    if num_lines >= 2630:
        stage_id = 5
    return stage_id, num_lines / 2630.0 * 100.0
