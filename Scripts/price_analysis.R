library(tidyjson)
library(dplyr)
library(rstudioapi)
library(ggplot2)
library(ggthemes)
library(cowplot)

here = dirname(rstudioapi::getActiveDocumentContext()$path)
news.file = paste0(here, '/news_database_clean-news.csv')
price.file = paste0(here, '/news_database_clean-price.csv')
dir.create(paste0(here, '/plots'), showWarnings=FALSE)
plot.filebase = paste0(here, '/plots/', Sys.Date())
dir.create(plot.filebase, showWarnings=FALSE)
plot.width = 800
plot.height= 450

## GET DATA ##
price = read.csv(price.file)
news = read.csv(news.file)
comb = merge(
  price, news,
  by=c('ticker', 'datetime')
)

comb$datetime <- as.Date(comb$datetime)
date.max <- max(comb$datetime, na.rm=TRUE)
comb$sign <- -1
comb$sign[comb$change_pct > 0] <- 1
comb$change_pct.log <- log(abs(comb$change_pct)) * comb$sign
#comb$change_pct <- comb$change_pct.log
## PLOT: scatter vader-titles
comb.plot.title <- subset(comb, vader_title_compound != 0)
scatter.title <- ggplot(
  comb.plot.title,
  aes(
    x=change_pct,
    y=vader_title_compound,
    color=best_article_title,
    alpha=best_article_title
  )
)
scatter.title <- scatter.title + geom_point()
scatter.title <- scatter.title + labs(
  title='closing %change vs vader sentiment of article (title)',
  x='%change of stock price',
  y='combined vader sentiment'
)
scatter.title <- scatter.title + geom_vline(xintercept=0)
scatter.title <- scatter.title + geom_hline(yintercept=0)
#scatter.title <- scatter.title + theme_fivethirtyeight()

scatter.plotfile <- paste0(plot.filebase, '/scatter_vader_titles.png')
png(
  scatter.plotfile,
  height=plot.height,
  width=plot.width
)
print(scatter.title)
dev.off()

#PLOT: scatter vader-blurbs
comb.plot.blurb <- subset(comb, vader_blurb_compound != 0)
scatter.blurb <- ggplot(
  comb.plot.blurb,
  aes(
    x=change_pct,
    y=vader_blurb_compound,
    color=best_article_blurb,
    alpha=best_article_blurb
  )
)
scatter.blurb <- scatter.blurb + geom_point()
scatter.blurb <- scatter.blurb + labs(
  title='closing %change vs vader sentiment of article (blurb)',
  x='%change of stock price',
  y='combined vader sentiment'
)
scatter.blurb <- scatter.blurb + geom_vline(xintercept=0)
scatter.blurb <- scatter.blurb + geom_hline(yintercept=0)

scatter.plotfile <- paste0(plot.filebase, '/scatter_vader_blurbs.png')
png(
  scatter.plotfile,
  height=plot.height,
  width=plot.width
)
print(scatter.blurb)
dev.off()

#PLOT: combined title vs blurb
scatter.comb <- plot_grid(
  scatter.title, scatter.blurb,
  align='v',
  nrow=2
)
scatter.plotfile <- paste0(plot.filebase, '/scatter_vader_combined.png')
png(
  scatter.plotfile,
  height=plot.height,
  width=plot.width
)
print(scatter.comb)
dev.off()

## PLOT: vader on latest day
comb.plot.title <- subset(comb, vader_title_compound != 0 & datetime == date.max)
scatter.title <- ggplot(
  comb.plot.title,
  aes(
    x=change_pct,
    y=vader_title_compound,
    color=best_article_title,
    alpha=best_article_title
  )
)
scatter.title <- scatter.title + geom_point()
scatter.title <- scatter.title + labs(
  title='closing %change vs vader sentiment of article (title)',
  x='%change of stock price',
  y='combined vader sentiment'
)
scatter.title <- scatter.title + geom_vline(xintercept=0)
scatter.title <- scatter.title + geom_hline(yintercept=0)
#scatter.title <- scatter.title + theme_fivethirtyeight()

scatter.plotfile <- paste0(plot.filebase, '/scatter_vader_titles-latest.png')
png(
  scatter.plotfile,
  height=plot.height,
  width=plot.width
)
print(scatter.title)
dev.off()

#PLOT: scatter vader-blurbs
comb.plot.blurb <- subset(comb, vader_blurb_compound != 0 & datetime == date.max)
scatter.blurb <- ggplot(
  comb.plot.blurb,
  aes(
    x=change_pct,
    y=vader_blurb_compound,
    color=best_article_blurb,
    alpha=best_article_blurb
  )
)
scatter.blurb <- scatter.blurb + geom_point()
scatter.blurb <- scatter.blurb + labs(
  title='closing %change vs vader sentiment of article (blurb)',
  x='%change of stock price',
  y='combined vader sentiment'
)
scatter.blurb <- scatter.blurb + geom_vline(xintercept=0)
scatter.blurb <- scatter.blurb + geom_hline(yintercept=0)

scatter.plotfile <- paste0(plot.filebase, '/scatter_vader_blurbs-latest.png')
png(
  scatter.plotfile,
  height=plot.height,
  width=plot.width
)
print(scatter.blurb)
dev.off()

#PLOT: combined title vs blurb
scatter.comb <- plot_grid(
  scatter.title, scatter.blurb,
  align='v',
  nrow=2
)
scatter.plotfile <- paste0(plot.filebase, '/scatter_vader_combined-latest.png')
png(
  scatter.plotfile,
  height=plot.height,
  width=plot.width
)
print(scatter.comb)
dev.off()