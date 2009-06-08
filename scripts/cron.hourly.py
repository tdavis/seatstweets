#! /usr/bin/env python

import twitter, re, urllib
from lxml import etree
from mx.DateTime.Parser import DateTimeFromString, DateFromString
from datetime import date, timedelta, datetime
from optparse import OptionParser

############################## EDIT HERE ############################## 
# Your API Token
PARAMS = { 'token': 'TOKEN' }
API_URL = 'http://ticketstumbler.com/api/1.0/rest'
# Your bit.ly credentials
BITLY = {
    'login': 'LOGIN',
    'apiKey': 'APIKEY',
    'version': '2.0.1',
    # So it inserts into bit.ly analytics
    'history': '1'
}
# Your Twitter password (this app assuming you use the same password
# for each account, which just makes thing simpler.)
TWITTER_PASSWORD = 'PASSWORD'
# Mapping of twitter names to category IDs
TWITTER_ACCOUNTS = (
    ('ST_MLB', 3),
    ('ST_NBA', 8),
    ('ST_NHL', 11)
)
############################## STOP EDIT ############################## 

def get_api_tree(ns, method, **params):
    """
    Makes an API request and returns an C{lxml.etree} `tree`.

    @param ns: An API namespace.
    @param method: An API method name.
    @param **params: The API query parameters.
    @returns: tree
    """
    params.update(PARAMS)
    # Path
    req = '%s/%s/%s.xml' % (API_URL, ns, method)
    # Query parameters
    req = '?'.join((req,urllib.urlencode(params)))
    result = urllib.urlopen(req)
    tree = etree.parse(result)
    return tree

def mktweet(*args):
    """
    Somewhat superfluous DRY method
    """
    return '%s %s. Tickets from $%.2f: %s' % args


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-t', '--today', dest='today', action='store_true',
        default=False)
    (opts, args) = parser.parse_args()
    if opts.today:
        regex = r'(.+?)\s(TODAY!\sat[^\.]+)'
    else:
        regex = r'(.+?)\son\s(.+?\sat[^\.]+)'

    for (name, cid) in TWITTER_ACCOUNTS:
        api = twitter.Api(username=name, password=TWITTER_PASSWORD)
        find_date = None
        statuses = api.GetUserTimeline(name)
        # Find the latest relevant tweet
        for s in statuses:
            txt = s.text
            match = re.search(regex, txt)
            if match:
                status = s
                find_date = DateTimeFromString(match.groups()[1])
                break
        start = date.today()
        if opts.today:
            end = date.today() + timedelta(days=1)
        else:
            start = date.today() + timedelta(days=1)
            end = date.today() + timedelta(days=8)
        kwargs = {
            'category_id': cid,
            'date_start': start,
            'date_end': end
        }
        tree = get_api_tree('event', 'search', **kwargs)
        for event in tree.iter('event'):
            when = DateTimeFromString(event.find('when').text)
            if not find_date or when >= find_date:
                # We found one!
                event_name = event.find('name').text
                if event_name[0:30] in status.text:
                    continue
                if opts.today:
                    when_day = 'TODAY!'
                else:
                    when_day = when.strftime('on %A, %B %d')
                when_time = when.strftime('at %I:%M %p')
                when_str = ' '.join((when_day, when_time))
                min_price = float(event.find('min_price').text)
                # bit.ly time
                kwargs = { 'longUrl': event.find('url').text }
                kwargs.update(BITLY)
                req = 'http://api.bit.ly/shorten?%s' % urllib.urlencode(kwargs)
                # Okay, this is kinda lazy
                result = eval(urllib.urlopen(req).read())
                rr = result['results']
                bitly_url = rr[rr.keys()[0]]['shortUrl']
                # Tweet
                tweet = mktweet(event_name, when_str, min_price, bitly_url)
                # Length check!
                if len(tweet) > 140:
                    hatchet = -(len(tweet) - 137)
                    event_name = event_name[0:hatchet]+'...'
                    tweet = mktweet(event_name, when_str, min_price, bitly_url)
                api.PostUpdate(tweet)
		if not opts.today:
                    break

