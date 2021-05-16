from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import re

STAGE_START_PATTERN = re.compile('^Starting phase (\d)/.*')
STAGE_END_PATTERN = re.compile('^Time for phase (\d)/.*')

def format_age(age: timedelta) -> str:
    hours = age.seconds // 3600
    minutes = (age.seconds % 3600) // 60
    seconds = (age.seconds % 3600) % 60
    if age.days > 0:
        return f'{age.days} days {hours:02d}:{minutes:02d}:{seconds:02d}'
    else:
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def check_chiabox_docker_status():
    try:
        output = subprocess.check_output(
            ['docker', 'inspect', '-f', '{{.State.Status}}', 'chiabox'])
        return output.decode('utf-8').strip()
    except subprocess.CallProcessError as e:
        return 'not yet'
