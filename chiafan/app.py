import os
import click
import logging

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
        'jobs': [status.to_payload() for status in ChiaManager().get_status()]
    }


@click.command()
@click.option('--log_dir', default = '/tmp',
              type = click.STRING, help = 'Whether to put the logs')
@click.option('--init_plotting_space', default = '/plotting/temp',
              type = click.STRING, help = 'Plotting space')
@click.option('--init_destination', default = '/plotting/dest',
              type = click.STRING, help = 'Destination')
@click.option('--farm_key', default = '',
              type = click.STRING, help = 'Farm key')
@click.option('--pool_key', default = '',
              type = click.STRING, help = 'Pool Key')
@click.option('--is_mock', default = False,
              type = click.BOOL, help = 'Whether to run plotter simulator')
def main(log_dir, init_plotting_space, init_destination, farm_key, pool_key, is_mock):
    # TODO(breakds): Support chia (in addtion to chiafunc) as well
    ChiaManager().run(pool_key = '1234', farm_key = '4567')
    app.run(host = '0.0.0.0')


if __name__ == '__main__':
    main()
