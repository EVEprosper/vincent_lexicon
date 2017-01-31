library(tidyjson)
library(dplyr)
library(rstudioapi)
library(jsonlite)

here = dirname(rstudioapi::getActiveDocumentContext()$path)
news.file = paste0(dirname(here), '/vincent_lexicon/tables/news_database.json')

news.rawdata <- fromJSON(news.file, simplifyDataFrame=TRUE)
news.str <- readChar(news.file, file.info(news.file)$size)
news.data <- news.str %>%
  gather_array %>%
  spread_values(
    'date'=jstring('datetime'),
    'ticker'=jstring('ticker'))
  # ) %>%
  # enter_object('price') %>%
  # spread_values(
  #   'change_pct'=jnumber('change_pct'),
  #   'close'=jnumber('close'),
  #   'source'=jstring('source')
  # )