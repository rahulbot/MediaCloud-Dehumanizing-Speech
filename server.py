import logging
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import datetime
import os
import mediacloud.api

# setup logging
logging.basicConfig(level=logging.DEBUG,
                    format="[%(asctime)s][%(levelname)s] %(name)s %(filename)s:%(funcName)s:%(lineno)d | %(message)s")
logger = logging.getLogger(__name__)
logger.info("---------------------------------------------------------------------------")

load_dotenv()   # load in config from loca file or env_vars

app = Flask(__name__)

MAX_SOURCE_MATCHES = 20

mc = mediacloud.api.MediaCloud(os.getenv('MC_API_KEY'))

SPEECH_QUERY = '"illegal immigrant" OR "illegal immigrants" OR "illegal alien" OR "illegal aliens" OR illegals OR "chain migration" OR "anchor baby" OR "anchor babies" OR "criminal alien" OR "criminal aliens" OR "flood immigrants"~10 OR "flood migrants"~10 OR "surge immigrants"~10 OR "surge migrants"~10 OR "wave immigrants"~10 OR "wave migrants"~10 OR "immigrant invasion"~10 OR "immigrants invading"~10 OR  "migrant invasion"~10 OR "migrants invading"~10 OR "catch and release"';
IMMIGRATION_QUERY = 'immigra*'
DATE_QUERY = 'publish_day:[2017-01-20T00:00:00Z TO 2019-09-01T00:00:00Z]';
DATE_QUERY_2014 = 'publish_day:[2014-01-01T00:00:00Z TO 2015-01-01T00:00:00Z]';
DATE_QUERY_2018 = 'publish_day:[2018-01-01T00:00:00Z TO 2019-01-01T00:00:00Z]';

SECONDS_IN_A_DAY = 86400


@app.route("/")
def index():
    return render_template("home.html",
                           matomo_host=os.getenv('MATOMO_HOST'),
                           matomo_site_id=os.getenv('MATOMO_SITE_ID'))


@app.route("/api/media/search.json", methods=['POST'])
def media_search():
    search_str = request.form.get('searchStr')
    if len(search_str) < 3:  # don't search for short strings
        matching_sources = []
    else:
        # TODO: limit this to english language sources?
        matching_sources = mc.mediaList(name_like=search_str, rows=MAX_SOURCE_MATCHES, sort="num_stories")
        matching_sources = [{'media_id': m['media_id'], 'name': m['name']} for m in matching_sources]
    return jsonify(matching_sources)


def _difference(query):
    fourteen = mc.storyCount(query, DATE_QUERY_2014)['count']
    eighteen = mc.storyCount(query, DATE_QUERY_2018)['count']
    delta = float(eighteen) / float(fourteen)
    return {
        'stories-2014': fourteen,
        'stories-2018': eighteen,
        'increase': delta,
    }


@app.route("/api/stories/change.json")
def story_change():
    media_id = request.args.get('mediaId')
    results = {
        'increase': {
            'denigrating': _difference("(" + SPEECH_QUERY + ") AND (media_id:" + media_id + ")"),
            'immigration': _difference("(" + IMMIGRATION_QUERY + ") AND (media_id:" + media_id + ")"),
        }
    }
    return jsonify(results)


@app.route("/api/stories/counts.json")
def story_counts():
    media_id = request.args.get('mediaId')
    media = mc.media(media_id)
    results = {
        'media': media,
        'counts': {
            'denigrating': mc.storyCount("(" + SPEECH_QUERY + ") AND (media_id:" + media_id + ")", DATE_QUERY),
            'immigration': mc.storyCount("(" + IMMIGRATION_QUERY + ") AND (media_id:" + media_id + ")", DATE_QUERY),
            'total': mc.storyCount("(*) AND (media_id:" + media_id + ")", DATE_QUERY),
        },
        'attention': {
        }
    }
    results['attention']['denigrating'] = weekly_story_count("(" + SPEECH_QUERY + ") AND (media_id:" + media_id + ")")
    results['attention']['immigration'] = weekly_story_count("(" + IMMIGRATION_QUERY + ") AND (media_id:" + media_id + ")")
    results['attention']['total'] = weekly_story_count("(*) AND (media_id:" + media_id + ")")

    return jsonify(results)


def weekly_story_count(query):
    return group_by_week(fill_in_date_range(mc.storyCount(query, DATE_QUERY, split=True)['counts']))


def fill_in_date_range(split_story_count_results):
    timestamped_counts = [{'count': c['count'],
                           'timestamp': int(datetime.datetime.strptime(c['date'][:10], '%Y-%m-%d').timestamp())}
                          for c in split_story_count_results]
    filled_in = []
    idx = 0
    last_timestamp = 0
    while idx < len(timestamped_counts):
        current_data = timestamped_counts[idx]
        while (last_timestamp > 0) and ((current_data['timestamp'] - last_timestamp) > SECONDS_IN_A_DAY):
            last_timestamp += SECONDS_IN_A_DAY
            filled_in.append({'count': 0, 'timestamp': last_timestamp})
        filled_in.append(current_data)
        last_timestamp = current_data['timestamp']
        idx += 1
    return filled_in


def group_by_week(daily_counts):
    with_week = [{'week': datetime.datetime.fromtimestamp(c['timestamp']).date().isocalendar()[1],
                  'count': c['count'],
                  'timestamp': c['timestamp']} for c in daily_counts]
    weekly_counts = []
    last_week = None
    current_week = None
    for c in with_week:
        if c['week'] != last_week:
            if current_week is not None:
                weekly_counts.append(current_week)
            current_week = {'count': c['count'], 'timestamp': c['timestamp']}
            last_week = c['week']
        else:
            current_week['count'] += c['count']
    return weekly_counts[1:-1]  # the first one is often a partial week, as is the last one


if __name__ == "__main__":
    app.debug = True
    app.run()
