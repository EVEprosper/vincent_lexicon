"""A utility that pulls down news data for processing and grading"""

from os import path

import requests
import demjson
import pandas_datareader.data as web
from tinydb import TinyDB, Query
import ujson as json
from plumbum import cli

import prosper.common.prosper_logging as p_logging
import prosper.common.prosper_config as p_config

HERE = path.abspath(path.dirname(__file__))
CONFIG_ABSPATH = path.join(HERE, 'vincent_config.cfg')
ME = 'NewsScraper'

CONFIG = None
LOGGER = p_logging.DEFAULT_LOGGER

class NewsScraper(cli.Application):
    """Plumbum CLI application to fetch EOD data and news articles"""
    _log_builder = p_logging.ProsperLogging(
        ME,
        config=CONFIG
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

    stock_list = path.join(HERE, CONFIG.get(ME, 'stock_list'))
    @cli.switch(
        ['--stock_list'],
        str,
        help='Path to alternate stock list (CSV: Ticker, Exchange)'
    )
    def override_stock_list(self, stock_list_path):
        """change stock list at runtime"""
        if path.isfile(stock_list_path):
            self.stock_list = stock_list_path
        else:
            raise FileNotFoundError

    def main(self):
        """Program Main flow"""
        global LOGGER
        if not self.debug:
            self._log_builder.configure_discord_logger()
        LOGGER = self._log_builder.logger
        LOGGER.debug('Hello world')

if __name__ == '__main__':
    NewsScraper.run()
