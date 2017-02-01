from datetime import datetime
from os import path, makedirs, remove
import csv
from enum import Enum

from tinydb import TinyDB, Query
import ujson as json
from plumbum import cli
import pandas as pd

import prosper.common.prosper_logging as p_logging

HERE = path.abspath(path.dirname(__file__))
ROOT = path.dirname(HERE)
ME = 'tablefy'

LOGGER = p_logging.DEFAULT_LOGGER   #load with null logger
LOG_PATH = path.join(HERE, 'logs')
makedirs(LOG_PATH, exist_ok=True)

def process_price_data(dataset):
    """crunch down entries into more R-friendly shape

    Args:
        dataset (:obj:`dict`): json-parsed tinyDB file

    Returns:
        (:obj:`list`): patterned data ready for pandas

    """
    LOGGER.info('--Processing price data from archive')
    data_list = []
    for key in cli.terminal.Progress(dataset['_default']):
        entry = dataset['_default'][key]    #Progress iterator only yields `key`
        row = {}
        row['ticker']       = entry['ticker']
        row['datetime']     = entry['datetime']
        row['change_pct']   = entry['price']['change_pct']
        row['close']        = entry['price']['close']
        row['price_source'] = entry['price']['source']
        data_list.append(row)
    return data_list

class UpOrDown(Enum):
    POSITIVE = 'positive'
    NEGATIVE = 'negative'
    NEUTRAL = 'neutral'

def check_price(data_entry, neutral_band=0.1):
    """check price information and set UpOrDown Enum

    Args:
        data_entry(:obj:`dict`) single entry from tinyDB
        neutral_band(float, optional): value to set "neutral" value
    Returns:
        (:enum:`UpOrDown`)

    """
    change_pct = data_entry['price']['change_pct']
    if abs(change_pct) < neutral_band:
        return UpOrDown.NEUTRAL
    elif change_pct > 0:
        return UpOrDown.POSITIVE
    elif change_pct < 0:
        return UpOrDown.NEGATIVE
    else:
        raise ValueError

def process_news_data(dataset):
    """crunch down entries into more R-friendly shape

    Args:
        dataset (:obj:`dict`): json-parsed tinyDB file

    Returns:
        (:obj:`list`): patterned data ready for pandas

    """
    LOGGER.info('--Processing price data from archive')
    data_list = []
    for key in cli.terminal.Progress(dataset['_default']):
        entry = dataset['_default'][key]    #Progress iterator only yields `key`
        pre_list = []
        best_article_title = 0
        best_article_blurb = 0
        best_article_title_index = None
        best_article_blurb_index = None
        direction = check_price(entry)
        article_index = 0
        for article in entry['news']:
            row = {}
            row['ticker']   = entry['ticker']
            row['datetime'] = entry['datetime']
            row['source']   = article['source']
            row['article_datetime'] = article['datetime']
            row['vader_title_neg']      = article['data']['vader_title']['neg']
            row['vader_title_neu']      = article['data']['vader_title']['neu']
            row['vader_title_pos']      = article['data']['vader_title']['pos']
            row['vader_title_compound'] = article['data']['vader_title']['compound']
            row['vader_blurb_neg']      = article['data']['vader_title']['neg']
            row['vader_blurb_neu']      = article['data']['vader_title']['neu']
            row['vader_blurb_pos']      = article['data']['vader_title']['pos']
            row['vader_blurb_compound'] = article['data']['vader_title']['compound']
            row['best_article_blurb'] = None
            row['best_article_title'] = None
            pre_list.append(row)

            #This is dumb, but easy
            if direction == UpOrDown.POSITIVE:
                if row['vader_title_compound'] > best_article_title:
                    best_article_title = row['vader_title_compound']
                    best_article_title_index = article_index
                if row['vader_blurb_compound'] > best_article_blurb:
                    best_article_blurb = row['vader_blurb_compound']
                    best_article_blurb_index = article_index
            elif direction == UpOrDown.NEGATIVE:
                if row['vader_title_compound'] < best_article_title:
                    best_article_title = row['vader_title_compound']
                    best_article_title_index = article_index
                if row['vader_blurb_compound'] < best_article_blurb:
                    best_article_blurb = row['vader_blurb_compound']
                    best_article_blurb_index = article_index

            article_index += 1

        if best_article_title_index:
            pre_list[best_article_title_index]['best_article_title'] = True

        if best_article_blurb_index:
            pre_list[best_article_title_index]['best_article_blurb'] = True

        data_list.extend(pre_list)
    return data_list

def csv_dump(rawdata, filepath):
    """push data out to CSV for processing later

    Args:
        data (:obj:`list`): listified data for pandas
        filepath (str): path to outfile

    """
    LOGGER.info('--dumping to file: ' + filepath)
    data = pd.DataFrame(rawdata)
    data.to_csv(
        filepath,
        index=False,
    )

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

    out_file = path.join(HERE, 'news_database_clean.csv')
    @cli.switch(
        ['-o', '--outfile'],
        str,
        help='path to output file'
    )
    def override_out_file(self, outfile):
        """set up path to output file"""
        self.out_file = path.abspath(outfile)

    def main(self):
        """Program Main flow"""
        global LOGGER
        LOGGER = self._log_builder.logger
        LOGGER.debug('hello world')

        #TODO: change to tinyDB handle?
        LOGGER.info('loading table file: ' + self.table_file)
        db_file = None
        with open(self.table_file, 'r') as json_fh:
            db_file = json.load(json_fh)

        LOGGER.info('processing table file')
        crunched_price_data = process_price_data(db_file)
        crunched_news_data = process_news_data(db_file)

        LOGGER.info('writing summary tables')
        price_csv_file = self.out_file.replace('.csv', '-price.csv')
        csv_dump(
            crunched_price_data,
            price_csv_file
        )

        news_csv_file = self.out_file.replace('.csv', '-news.csv')
        csv_dump(
            crunched_news_data,
            news_csv_file
        )

if __name__ == '__main__':
    Tablefy.run()
