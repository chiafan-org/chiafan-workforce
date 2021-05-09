import os
import click

from flask import current_app, g, Flask, redirect
from .states import PlottingSummary


if __name__ == '__main__':
    summary = PlottingSummary('/a/b/c', '/d/e/f', 95.3)
    print(summary)
