import urllib,urllib2,json,re,datetime,sys,cookielib
from .. import models
from pyquery import PyQuery
import re
import traceback

class TweetManager:

	def __init__(self):
		pass

	@staticmethod
	def getTweets(tweetCriteria, tweetFlag, receiveBuffer=None, bufferLength=100, proxy=None):
		refreshCursor = ''

		results = []
		resultsAux = []
		cookieJar = cookielib.CookieJar()

		if hasattr(tweetCriteria, 'username') and (tweetCriteria.username.startswith("\'") or tweetCriteria.username.startswith("\"")) and (tweetCriteria.username.endswith("\'") or tweetCriteria.username.endswith("\"")):
			tweetCriteria.username = tweetCriteria.username[1:-1]

		active = True

		totalNumTweets = 0

		while active:
			json, fullurl = TweetManager.getJsonReponse(tweetCriteria, refreshCursor, cookieJar, proxy)
			if len(json['items_html'].strip()) == 0:
				break

			refreshCursor = json['min_position']
			# print ("refreshCursor is {}".format(refreshCursor))

			tweets = PyQuery(json['items_html'])('div.js-stream-tweet')

			# print ("the number of tweets {}".format(len(tweets)))

			totalNumTweets += len(tweets)



			if len(tweets) == 0:
				break

            # not parse the tweet
			if not tweetFlag:
				if tweetCriteria.maxTweets > 0 and len(results) >= tweetCriteria.maxTweets:
					active = False
				continue

			for tweetHTML in tweets:
				tweetPQ = PyQuery(tweetHTML)
				tweet = models.Tweet()

				try:
					usernameTweet = tweetPQ("span:first.username.u-dir b").text()
				except Exception as e:
					usernameTweet = ""
					print ("can not get username")
				try:
					# get text in different tag seperated by \n
					tweet_text = tweetPQ("p.js-tweet-text").text(squash_space=False)
					tweet_text_list = tweet_text.split("\n")
					# replace the "" with " ", for the \n\n situation
					for i, v in enumerate(tweet_text_list):
						if v == "":
							tweet_text_list[i] = " "
					txt = "".join(tweet_text_list)
					# print(" ".join(re.compile('(#\\w*)').findall(txt)))
					
				except Exception as e:
					txt = ""
					print ("can not get txt")
					traceback.print_exc()
				
				try:
					reply = int(tweetPQ("span.ProfileTweet-action--reply span.ProfileTweet-actionCount").attr("data-tweet-stat-count").replace(",", ""))
				except Exception as e:
					reply = 0
					print ("can not get retweets.")
					traceback.print_exc()

				try:
					retweets = int(tweetPQ("span.ProfileTweet-action--retweet span.ProfileTweet-actionCount").attr("data-tweet-stat-count").replace(",", ""))
				except Exception as e:
					retweets = 0
					print ("can not get retweets")
					traceback.print_exc()
					
				try:
					favorites = int(tweetPQ("span.ProfileTweet-action--favorite span.ProfileTweet-actionCount").attr("data-tweet-stat-count").replace(",", ""))
				except Exception as e:
					favorites = 0
					print ("can not get retweets.")
					traceback.print_exc()
					
				try:
					dateSec = int(tweetPQ("small.time span.js-short-timestamp").attr("data-time"))
				except Exception as e:
					dateSec = 0
					print ("can not get dateSec")
					traceback.print_exc()
					
				try:
					idx = tweetPQ.attr("data-tweet-id")
				except Exception as e:
					idx = ""
					print ("can not get id")
					traceback.print_exc()
					
				try:
					permalink = tweetPQ.attr("data-permalink-path")
				except Exception as e:
					permalink = ""
					print ("can not get permalink")
					traceback.print_exc()
					
				try:
					url = tweetPQ('a.twitter-timeline-link').attr('data-expanded-url')
				except Exception as e:
					url = ""
					print ("can not get url")
					traceback.print_exc()
					
				tweet.url = url
                # hashtag
				try:
					hashtags = tweetPQ('a.twitter-hashtag.pretty-link.js-nav').text().replace("# ", "#")
				except Exception as e:
					hashtags = ""
					traceback.print_exc()
					
				tweet.hashtags = hashtags.replace('\n', '')

				geo = ''
				try:
					geoSpan = tweetPQ('span.Tweet-geo')
					if len(geoSpan) > 0:
						geo = geoSpan.attr('title')
				except Exception as e:
					geo = ''



				tweet.id = idx
				tweet.permalink = 'https://twitter.com' + permalink
				tweet.username = usernameTweet
				tweet.text = txt
				tweet.date = datetime.datetime.fromtimestamp(dateSec)
				tweet.reply = reply
				tweet.retweets = retweets
				tweet.favorites = favorites
				tweet.mentions = " ".join(re.compile('(@\\w*)').findall(tweet.text))
				# tweet.hashtags = " ".join(re.compile('(#\\w*)').findall(tweet.text))
				tweet.geo = geo

				results.append(tweet)
				resultsAux.append(tweet)

				if receiveBuffer and len(resultsAux) >= bufferLength:
					receiveBuffer(resultsAux)
					resultsAux = []

				if tweetCriteria.maxTweets > 0 and len(results) >= tweetCriteria.maxTweets:
					active = False
					break

		print ("url: {}".format(fullurl))

		if receiveBuffer and len(resultsAux) > 0:
			receiveBuffer(resultsAux)

		return results, totalNumTweets

	@staticmethod
	def getJsonReponse(tweetCriteria, refreshCursor, cookieJar, proxy):
        # add l=en, only get english tweets
		# url = "https://twitter.com/i/search/timeline?f=tweets&q=%s&src=typd&max_position=%s"
		url = "https://twitter.com/i/search/timeline?f=tweets&q=%s&src=typd&l=en&max_position=%s"

		urlGetData = ''

		if hasattr(tweetCriteria, 'username'):
			urlGetData += ' from:' + tweetCriteria.username

		if hasattr(tweetCriteria, 'querySearch'):
			urlGetData += ' ' + tweetCriteria.querySearch

		if hasattr(tweetCriteria, 'near'):
			urlGetData += "&near:" + tweetCriteria.near + " within:" + tweetCriteria.within

		if hasattr(tweetCriteria, 'since'):
			urlGetData += ' since:' + tweetCriteria.since

		if hasattr(tweetCriteria, 'until'):
			urlGetData += ' until:' + tweetCriteria.until


		if hasattr(tweetCriteria, 'topTweets'):
			if tweetCriteria.topTweets:
				url = "https://twitter.com/i/search/timeline?q=%s&src=typd&max_position=%s"

		# if hasattr(tweetCriteria, 'lang'):
		# 	urlLang = 'l=' + tweetCriteria.lang + '&'
		# else:
		# 	urlLang = ''

		# url = url % (urllib.parse.quote(urlGetData), urlLang, refreshCursor)
		url = url % (urllib.quote(urlGetData), refreshCursor)
		# print ("url: {}".format(url))
		headers = [
			('Host', "twitter.com"),
			('User-Agent', "Chrome/66.0.3359.181"),
			('Accept', "application/json, text/javascript, */*; q=0.01"),
			('Accept-Language', "de,en-US;q=0.7,en;q=0.3"),
			('X-Requested-With', "XMLHttpRequest"),
			('Referer', url),
			('Connection', "keep-alive")
		]

		if proxy:
			opener = urllib2.build_opener(urllib2.ProxyHandler({'http': proxy, 'https': proxy}), urllib2.HTTPCookieProcessor(cookieJar))
		else:
			opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookieJar))
		opener.addheaders = headers

		try:
			response = opener.open(url)
			jsonResponse = response.read()
		except:
			print "Twitter weird response. Try to see on browser: https://twitter.com/search?q=%s&src=typd" % urllib.quote(urlGetData)
			sys.exit()
			return

		dataJson = json.loads(jsonResponse)

		return dataJson, url
