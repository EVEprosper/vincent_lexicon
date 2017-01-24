"""A utility that pulls down news data for processing and grading"""

from datetime import datetime
from os import path, makedirs, remove
import csv

import requests
import demjson
import pandas_datareader.data as web
from tinydb import TinyDB, Query
import ujson as json
from plumbum import cli
from nltk import download as nltk_download
import nltk.sentiment as sentiment
from six.moves.html_parser import HTMLParser

from _version import __version__
import prosper.common.prosper_logging as p_logging
import prosper.common.prosper_config as p_config

HERE = path.abspath(path.dirname(__file__))
CONFIG_ABSPATH = path.join(HERE, 'vincent_config.cfg')
ME = 'NewsScraper'

CONFIG = p_config.ProsperConfig(CONFIG_ABSPATH)
LOGGER = p_logging.DEFAULT_LOGGER
LOG_PATH = CONFIG.get('LOGGING', 'log_path')

CACHE_PATH = path.join(HERE, CONFIG.get(ME, 'cache_path'))
makedirs(CACHE_PATH, exist_ok=True)

CALENDAR_CACHEFILE = path.join(CACHE_PATH, CONFIG.get(ME, 'calendar_cachefile'))
CALENDAR_CACHE = TinyDB(CALENDAR_CACHEFILE)
TRADIER_KEY = CONFIG.get(ME, 'tradier_key')
def market_open(
        cache_buster=False,
        calendar_cache=CALENDAR_CACHE,
        endpoint='https://api.tradier.com/v1/markets/calendar',
        auth_key=TRADIER_KEY
):
    """make sure the market is actually open today

    Note:
        uses https://developer.tradier.com/documentation/markets/get-calendar
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
        LOGGER.info('--checking cache')
        value = calendar_cache.search(day_query.date == today)
        LOGGER.debug(value)
        if value:
            LOGGER.info('--FOUND IN CACHE')
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

    LOGGER.info('--checking internet for calendar')

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
    LOGGER.info('--updating cache')
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

def fetch_news_info(
        ticker_list,
):
    """Process ticker_list and save news endpoints

    NOTE: Step1, needs to run as first step
    Args:
        ticker_list (:obj:`list` str): list of tickers to fetch news feeds on

    Returns:
        (:obj:`dict`): tinyDB-ready list of news info

    """
    LOGGER.info('--Fetching news items for tickers')
    processed_data = []
    failed_tickers = []
    empty_tickers = []
    last_exception = None
    for ticker in cli.terminal.Progress(ticker_list):
        try:
            news_data = fetch_news(ticker)
        except Exception as err_msg:
            #LOGGER.warning('WARNING: unable to parse news for ' + ticker)
            failed_tickers.append(ticker)
            last_exception = err_msg
            continue

        if not news_data:
            empty_tickers.append(ticker)
        else:
            try:
                data_entry = build_data_entry(ticker, news_data)
            except Exception as err_msg:
                LOGGER.warning(
                    'WARNING: unable to organize data for ' + ticker,
                    exc_info=True
                )
                failed_tickers.append(ticker)
                last_exception = err_msg
                continue
            processed_data.append(data_entry)

    LOGGER.info('empty_tickers={0}'.format(empty_tickers))
    if failed_tickers:
        LOGGER.error(
            'EXCEPTION FOUND: some tickers did not return news:' +
            '\n\tSEE LOG FOR SPECIFIC ERRORS' +
            '\n\tlast_exception={0}'.format(repr(last_exception)) +
            '\n\ttickers={0}'.format(failed_tickers)
        )
    return processed_data

def build_data_entry(ticker, news_data):
    """build the fundamental entry for tinyDB

    Args:
        ticker (str): company ticker
        news_data (:obj:`list`): collection of news data

    Returns:
        (:obj:`dict`) tinyDB ready object

    """
    LOGGER.info('--Formatting data for: ' + ticker)
    db_entry = {}
    db_entry['ticker'] = ticker
    db_entry['datetime'] = datetime.today().strftime('%Y-%m-%d') #TODO: add H:M:S?
    db_entry['news'] = news_data
    db_entry['version'] = __version__
    db_entry['price'] = {}

    ## Fetch price data ##
    price_df = web.get_quote_yahoo(ticker)
    db_entry['price']['change_pct'] = float(price_df['change_pct'].get_value(0).strip('%'))
    db_entry['price']['close'] = float(price_df['last'].get_value(0))
    try:
        db_entry['price']['PE'] = float(price_df['PE'].get_value(0))
    except ValueError:
        db_entry['price']['PE'] = None
    try:
        db_entry['price']['short_ratio'] = float(price_df['short_ratio'].get_value(0))
    except ValueError:
        db_entry['price']['short_ratio'] = None

    return db_entry


NEWS_SOURCE = CONFIG.get(ME, 'articles_uri')
def fetch_news(
        ticker,
        news_source=NEWS_SOURCE
):
    """Fetch individual ticker's news feed

    Args:
        ticker (str): stock ticker
        news_source (str, optional): news API endpoint

    Returns:
        (:obj:`list`) (adjusted) news JSON result

    """
    LOGGER.info('----Fetching news for ' + ticker)
    params = {
        'q': ticker,
        'output': 'json'
    }
    try:
        req = requests.get(
            news_source,
            params=params
        )
    except Exception as err_msg:
        LOGGER.warning(
            'EXCEPTION: unable to fetch news feed' +
            '\n\texception={0}'.format(repr(err_msg)) +
            '\n\turl={0}'.format(news_source) +
            '\n\tticker={0}'.format(ticker),
            exc_info=True
        )
        raise err_msg

    try:
        raw_articles = demjson.decode(req.text)
    except Exception as err_msg:
        LOGGER.debug(req.text)
        LOGGER.warning(
            'EXCEPTION: unable to parse news items' +
            '\n\texception={0}'.format(repr(err_msg)) +
            '\n\turl={0}'.format(news_source) +
            '\n\tticker={0}'.format(ticker),
            exc_info=True
        )
        raise err_msg
    news_list = []
    for block in raw_articles['clusters']:
        if int(block['id']) == -1:
            continue #last entry is weird
        for indx, story in enumerate(block['a']):
            story_info = process_story_info(story)
            if indx==0: #TODO: validate "primary" story is always first
                story_info['primary'] = True
            else:
                story_info['primary'] = False

            news_list.append(story_info)

    return news_list

def process_story_info(story_info):
    """crunch news into regular format

    Args:
        story_info (:obj:`dict`): news_feed['clusters'][block_index]['a'] contents

    Returns:
        (:obj:`dict`): processed article info

    """
    LOGGER.debug('----Processing story_info: ' + story_info['u'])
    parser = HTMLParser()   #http://stackoverflow.com/a/2087433
    info = {}
    info['source']   = story_info['s']
    info['url']      = story_info['u']
    info['title']    = parser.unescape(story_info['t'])
    info['blurb']    = parser.unescape(story_info['sp'])
    info['usg']      = story_info['usg'] #not sure if UUID is useful?
    info['datetime'] = datetime.\
        fromtimestamp(int(story_info['tt'])).\
        strftime('%Y-%m-%d %H-%M-%S')

    return info
    #Unused keys:
    #story_info['sru']  google reference link
    #story_info['d']    human-readable "when published" info

def configure_database_connection(
        table_name,
        table_dir=CACHE_PATH,
        debug=False
):
    """connects to database and returns usable handle

    Args:
        table_name (str): path to tinyDB table (abspath > relpath)
        debug (bool, optional): create/return "debug" table rather than prod

    Returns:
        (:obj:`tinydb.TinyDB`) usable handle for database operations

    """
    LOGGER.info('getting table connection: ' + table_name)
    table_path = path.join(table_dir, table_name)
    if not debug:
        table_handle = TinyDB(table_path)
    else:
        LOGGER.info('--DEBUG MODE')
        debug_path = path.join(table_dir, 'debug_' + table_name)
        try: #remove previous debug version
            LOGGER.debug('--removing old debug file: ' + debug_path)
            remove(debug_path)
        except FileNotFoundError:
            pass
        table_handle = TinyDB(debug_path)

    return table_handle

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

        ## Figure out tickers to query
        ticker_list = parse_stock_list(self.stock_list)
        LOGGER.debug(ticker_list)

        ## Fetch news articles (and configure tinyDB schema)
        news_feeds = fetch_news_info(ticker_list)
        LOGGER.debug(news_feeds)


        ## Last Step: write to database
        news_database = configure_database_connection(
            CONFIG.get(ME, 'news_database'),
            debug=self.debug
        )
        news_database.insert_multiple(news_feeds)

if __name__ == '__main__':
    NewsScraper.run()
