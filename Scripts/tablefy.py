from datetime import datetime
from os import path, makedirs, remove
import csv
from enum import Enum

from tinydb import TinyDB, Query
import ujson as json
from plumbum import cli

import prosper.common.prosper_logging as p_logging

HERE = path.abspath(path.dirname(__file__))
ROOT = path.dirname(HERE)
ME = 'tablefy'

LOGGER = p_logging.DEFAULT_LOGGER   #load with null logger
LOG_PATH = path.join(HERE, 'logs')
makedirs(LOG_PATH, exist_ok=True)
class Tablefy(cli.Application):
    """Plumbum CLI application to help pre-process tinyDB data into more regular table shape"""

    _log_builder = p_logging.ProsperLogger(
        ME,
        LOG_PATH
    )
    debug = cli.Flag(
        ['d', '--debug'],
        help='Debug mode, no production db, headless mode'
    )

    @cli.switch(
        ['-v', '--verbose'],
        help='Enable verbose messaging'
    )
    def enable_verbose(self):
        """toggle verbose logger"""
        self._log_builder.configure_debug_logger()

    table_file = path.join(ROOT, 'vincent_lexicon', 'tables', 'news_database.json')
    @cli.switch(
        ['-t', '--table'],
        str,
        help='path to table/tinyDB file'
    )
    def override_table_file(self, table):
        """validate path and update self.table_file"""
        if path.isfile(table):
            self.table_file = table
        else:
            raise FileNotFoundError

    def main(self):
        """Program Main flow"""
        global LOGGER
        LOGGER = self._log_builder.logger
        LOGGER.debug('hello world')

if __name__ == '__main__':
    Tablefy.run()
