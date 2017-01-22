"""A utility that pulls down news data for processing and grading"""

from os import path
import csv

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

CONFIG = p_config.ProsperConfig(CONFIG_ABSPATH)
LOGGER = p_logging.DEFAULT_LOGGER
LOG_PATH = CONFIG.get('LOGGING', 'log_path')
def parse_stock_list(
        stock_list_path,
        column_keyname='Symbol'
):
    """parse stock list into list of tickers

    Args:
        stock_list_path (str): Path to stock_list csv file
        column_keyname (str, optional): csv column keyname

    Returns:
        (:obj:`list` str): list of stock tickers

    """
    #print('--Parsing stock list: ' + stock_list_path)
    LOGGER.info('Parsing stock list: ' + stock_list_path)
    if not path.isfile(stock_list_path):
        raise FileNotFoundError(stock_list_path)

    ticker_list = []
    with open(stock_list_path, 'r') as csv_file:
        try:
            stock_csv = csv.DictReader(csv_file)
        except Exception as err_msg:
            LOGGER.error(
                'EXCEPTION: unable to parse stock list' +
                '\n\tstock_list_path={0}'.format(stock_list_path),
                exc_info=True
            )
            raise err_msg
        for row in stock_csv:   #TODO: have to read each line?
            ticker_list.append(row[column_keyname])
    LOGGER.info('Loaded tickers from file: x' + str(len(ticker_list)))
    LOGGER.debug(ticker_list)

    return ticker_list

class NewsScraper(cli.Application):
    """Plumbum CLI application to fetch EOD data and news articles"""
    _log_builder = p_logging.ProsperLogger(
        ME,
        LOG_PATH,
        config_obj=CONFIG
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
        ticker_list = parse_stock_list(self.stock_list)
if __name__ == '__main__':
    NewsScraper.run()
