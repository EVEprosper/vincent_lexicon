"""A utility that pulls down news data for processing and grading"""

from datetime import datetime
from os import path
import csv

import requests
import demjson
import pandas_datareader.data as web
from tinydb import TinyDB, Query
import ujson as json
from plumbum import cli
from nltk import download as nltk_download
import nltk.sentiment as sentiment

import prosper.common.prosper_logging as p_logging
import prosper.common.prosper_config as p_config

HERE = path.abspath(path.dirname(__file__))
CONFIG_ABSPATH = path.join(HERE, 'vincent_config.cfg')
ME = 'NewsScraper'

CONFIG = p_config.ProsperConfig(CONFIG_ABSPATH)
LOGGER = p_logging.DEFAULT_LOGGER
LOG_PATH = CONFIG.get('LOGGING', 'log_path')

CALENDAR_CACHEFILE = path.join(HERE, CONFIG.get(ME, 'calendar_cachefile'))
CALENDAR_CACHE = TinyDB(CALENDAR_CACHEFILE)
MARKET_CALENDAR_ENDPOINT = CONFIG.get(ME, 'calendar_endpoint')
TRADIER_KEY = CONFIG.get(ME, 'tradier_key')
def market_open(
        cache_buster=False,
        calendar_cache=CALENDAR_CACHE,
        endpoint=MARKET_CALENDAR_ENDPOINT,
        auth_key=TRADIER_KEY
):
    """make sure the market is actually open today

    Args:
        cache_buster (bool, optional): ignore cache, DEFAULT: False
        calendar_cache (:obj:`TinyDB`): cached version of market calendar
        endpoint (str, optional): address for fetching open days calendar (tradier)
        auth_key (str, optional): authentication for calendar endpoint

    Returns:
        (bool): is market open

    """
    LOGGER.info('Checking if market is open')
    today = datetime.today().strftime('%Y-%m-%d')
    day_query = Query()
    if not cache_buster:
        value = calendar_cache.search(day_query.date == today)
        LOGGER.debug(value)
        if value:
            if value[0]['status'] == 'closed':
                LOGGER.info('Markets closed today')
                calendar_cache.close()
                return False
            elif value[0]['status'] == 'open':
                LOGGER.info('Markets open today')
                calendar_cache.close()
                return True
            else:
                LOGGER.error(
                    'EXCEPTION: unexpected market status' +
                    '\n\tvalue={0}'.format(value)
                )
                calendar_cache.close()
                raise Exception #TODO make custom exception

    ## Fetch calendar from internet ##
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + auth_key
    }
    try:
        req = requests.get(
            endpoint,
            headers=headers
        )
        calendar = req.json()
    except Exception as err_msg:
        LOGGER.error(
            'EXCEPTION: unable to fetch calendar' +
            '\n\turl={0}'.format(endpoint),
            exc_info=True
        )
        calendar_cache.close()
        raise err_msg #TODO: no calendar behavior?

    ## update cache ##
    calendar_cache.insert_multiple(calendar['calendar']['days']['day'])

    value = calendar_cache.search(day_query.date == today)
    LOGGER.debug(value)
    if value[0]['status'] == 'closed':
        LOGGER.info('Markets closed today')
        calendar_cache.close()
        return False
    elif value[0]['status'] == 'open':
        LOGGER.info('Markets open today')
        calendar_cache.close()
        return True
    else:
        LOGGER.error(
            'EXCEPTION: unexpected market status' +
            '\n\tvalue={0}'.format(value)
        )
        calendar_cache.close()
        raise Exception #TODO make custom exception

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

NEWS_SOURCE = CONFIG.get(ME, 'articles_uri')
def fetch_news_info(
        ticker_list,
        news_source=NEWS_SOURCE
):
    """Process ticker_list and save news endpoints

    Args:
        ticker_list (:obj:`list` str): list of tickers to fetch news feeds on
        news_source (str, optional): endpoint to fetch data from (GOOGLE default)

    Returns:
        (:obj:`dict`): tinyDB-ready list of news info

    """
    pass

QUOTE_SOURCE = CONFIG.get(ME, 'quote_source')#TODO: needed?
def fetch_price(
        stock_ticker,
        quote_source=QUOTE_SOURCE #TODO: needed?
):
    """Get EOD price data for stock ticker

    Args:
        stock_ticker(str): stock ticker to query
        quote_source(str, optional): quote resource

    Returns:
        (dict?) return from pandas-datareader

    """
    pass


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

        if not nltk_download('vader_lexicon'):
            LOGGER.error('unable to load vader_lexicon for text analysis')
        else:
            text_analyzer = sentiment.vader.SentimentIntensityAnalyzer()

        if not market_open():
            LOGGER.info('Markets not open today')
            if not self.debug:  #keep running if debug
                exit()

        ticker_list = parse_stock_list(self.stock_list)
        news_feeds = fetch_news_info(ticker_list)
if __name__ == '__main__':
    NewsScraper.run()
