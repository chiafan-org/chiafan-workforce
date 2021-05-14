import os
import sys
import signal
import click
import logging
from pathlib import Path

from flask import current_app, g, Flask, redirect, render_template, request, url_for
from .chia_manager import ChiaManager


root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

app = Flask(__name__)
app.secret_key = b'\xb7\x0b\x86\xc0+\x1a&\xd6 \xdfx\\\x90O\xac\xae'
app.config['extra_fields'] = []


@app.route('/status', methods = [ 'GET', 'POST' ])
def handle_status():
    return {
        'server': ChiaManager().inspect(),
        'workers': ChiaManager().inspect_workers(),
        'jobs': [status.to_payload() for status in ChiaManager().get_status()],
    }


@app.route('/start', methods = [ 'GET', 'POST' ])
def handle_start():
    if ChiaManager().thread is None:
        num_workers = len(ChiaManager().workers)
        logging.info(f'Start running plotting jobs with {num_workers} workers.')
        ChiaManager().run()
    elif ChiaManager().draining:
        logging.info('Resume from draining')
        ChiaManager().run()
    return {
        'code': 'started'
    }


@app.route('/drain', methods = [ 'GET', 'POST' ])
def handle_drain():
    ChiaManager().drain()
    return {
        'code': 'drained'
    }


def cleanup(signum, frame):
    ChiaManager().ensure_shutdown()
    sys.exit(0)
    

@click.command()
@click.option('--farm_key', default = '',
              type = click.STRING, help = 'Farm key')
@click.option('--pool_key', default = '',
              type = click.STRING, help = 'Pool Key')
@click.option('workers', '--worker', multiple = True,
              type = click.STRING, help = 'a WORKSPACE:DESTINATION pair')
@click.option('--is_mock', default = False,
              type = click.BOOL, help = 'Whether to run plotter simulator')
@click.option('--port', default = '5000',
              type = click.STRING, help = 'Specify the port')
def main(workers, farm_key, pool_key, is_mock, port):
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    # TODO(breakds): Support chia (in addtion to chiafunc) as well
    ChiaManager().set_farm_key(farm_key)
    ChiaManager().set_pool_key(pool_key)
    for worker_spec in workers:
        workspace, destination = worker_spec.split(':')
        ChiaManager().add_worker(workspace = Path(workspace),
                                 destination = Path(destination),
                                 is_mock = is_mock)
    app.run(host = '0.0.0.0', port = port)


if __name__ == '__main__':
    main()
