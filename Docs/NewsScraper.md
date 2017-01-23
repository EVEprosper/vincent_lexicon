# NewsScraper
_Step 1 of data science: collect the data_

Though [prosperbot](https://github.com/EVEprosper/ProsperUtilities) has shown some promise, [NLTK](http://www.nltk.org/)'s [vader_lexicon](http://www.nltk.org/api/nltk.sentiment.html#module-nltk.sentiment.vader) has its limits.  Specifically, VADER does not understand corp-speak.  

In an effort to remedy this, we need to build up a new lexicon that properly weighs corperate terms such as `bankrupcy` and `anti trust`, as well as more complex phrases like `hitting targets` or `missing projections`.  To meet this goal, we're pairing news from [Google's Finance API](https://www.google.com/finance/company_news) with [Yahoo's EOD feed](http://pandas-datareader.readthedocs.io/en/latest/remote_data.html?highlight=get_quote_yahoo#yahoo-finance-quotes) to get news + bulk-sentiment data together.

NewsScraper is the data collection tool.  Designed to be run once-daily, it will collect, pre-process, and save news for as many tickers as you please.  It is also designed to be easy to deploy on a virgin system, and configurable to tune bulk collection behavior as needed (trim tickers without data, prefilter incoming data).  Lastly, it is integrated with [ProsperCommon's Logger](https://github.com/EVEprosper/ProsperCommon/blob/master/docs/prosper_logging.md) which has a pre-built handler for alerting a [Discord Webhook](https://support.discordapp.com/hc/en-us/articles/228383668-Intro-to-Webhooks) if things break.

## How It Works
NewsScraper is built on the back of [Plumbum](http://plumbum.readthedocs.io/en/latest/cli.html) to be run on any platform as a CLI cron or batch job.  Also we rely on the following sources for data:

* [Google's Finance News API](https://www.google.com/finance/company_news) -- Manually implemented
* [pandas-datareader](http://pandas-datareader.readthedocs.io/en/latest/index.html) for EOD price data
* [Tradier's Market Calendar](https://developer.tradier.com/documentation/markets/get-calendar) -- Manually implemented, need auth key

**additional prerequisites**
* [tinyDB](https://tinydb.readthedocs.io/en/latest/) -- noSQL store
* [ujson](https://pypi.python.org/pypi/ujson) -- faster JSON library
* [requests](http://docs.python-requests.org/en/master/) -- processing GET HTTP requests
* [demjson](https://pypi.python.org/pypi/demjson/2.2.4) -- processing malformed JSON from Google endpoint
* [NLTK](http://www.nltk.org/) -- first-pass sentiment analysis

Just launch NewsScraper.py (inside virtualenv) daily, and watch the data come in!

## Data Schema
vincent_lexicon is built (for now) off [TinyDB](https://tinydb.readthedocs.io/en/latest/) a local noSQL store.  Though the data might seem more complex at first, storing it this way will open up the possibility for more complex tools later, without being crippled by traditional-SQL schema design.  If productization is a goal, converting to [MongoDB](https://www.mongodb.com/) with [tinymongo](https://pypi.python.org/pypi/tinymongo) as an intermediary is an option.

```javascript
{[
  {
    "ticker": stock_ticker,
    "date": datetime.today(),
    "news":[
      {
        //individual stories from Google company_news endpoint
        "title": story_title,
        "source": story_source,
        "blurb": story_summary,
        "url": story_link,
        "datetime": story_publish_datetime
        "data":{
          "vader_scores":[positive_score, negative_score, composite],
          "publish_timeskew": market_closedatetime - story_publish_datetime 
        },
        "primary": bool
      }
    "price":{
      //data from get_quote_yahoo
      "close": last,
      "change_pct": change_pct,
      "PE": PE,
      "short_ratio": short_ratio
      "time": time
    }
  }
]}
```

This schema is designed to be able to query by `ticker` and group_by `date`.
        
