import os
import click

from flask import current_app, g, Flask, redirect
from .states import PlottingSummary
from .chia_manager import ChiaManager

app = Flask(__name__)
app.secret_key = b'\xb7\x0b\x86\xc0+\x1a&\xd6 \xdfx\\\x90O\xac\xae'
app.config['extra_fields'] = []

@app.route('/create_plot', methods = [ 'GET', 'POST' ])
def handle_create_plot():
    ChiaManager().create_plot()
    return {
        'success': True
    }

@app.route('/status', methods = [ 'GET', 'POST' ])
def handle_status():
    return {
        'numPlottingProcesses': len(ChiaManager().plotting_processes)
    }

@click.command()
@click.option('--use_chiafunc', default = True,
              type = click.BOOL, help = 'Whether to use the chiafunc command instead of chia')
def main(use_chiafunc):
    # TODO(breakds): Support chia (in addtion to chiafunc) as well
    app.run()


if __name__ == '__main__':
    main()
