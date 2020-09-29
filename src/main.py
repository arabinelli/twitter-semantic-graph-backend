import os
from typing import List, Optional
from warnings import warn
from collections import namedtuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .connectors.redis import RedisClient
from .connectors.twitter import TwitterClient
from .logic.network import NetworkBuilder

redis_client = RedisClient()

app = FastAPI()

origins = []

additional_origins = os.environ.get("ORIGINS")
if additional_origins:
    origins += additional_origins.split(",")
else:
    warn(
        "No env variable 'ORIGINS' was found."
        + "Ya know, generally speaking, nicht gut..."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GraphRequest(BaseModel):
    hashtags: List[str]
    languages: Optional[List[str]] = None
    filter_retweets: Optional[bool] = True
    filter_node_frequency: Optional[int] = 0
    filter_link_frequency: Optional[int] = 0


class TweetsRequest(BaseModel):
    hashtags: List[str]
    languages: Optional[List[str]] = None
    filter_retweets: Optional[bool] = True
    target_hashtag: str


Tweet = namedtuple("Tweet", ["id", "text", "screen_name", "username", "created_at"])


@redis_client.cache
def get_tweets(hashtags, filter_retweets, languages):
    twitter_client = TwitterClient()
    tweets, full_text = twitter_client.search_tweets_by_hashtags(
        hashtags, filter_retweets=filter_retweets, languages=languages,
    )
    if full_text:
        list_of_tweets = [
            Tweet(
                tweet.id,
                tweet.full_text,
                tweet.user.screen_name,
                tweet.user.name,
                tweet.created_at,
            )
            for tweet in tweets
        ]
    else:
        list_of_tweets = [
            Tweet(
                tweet.id,
                tweet.text,
                tweet.user.screen_name,
                tweet.user.name,
                tweet.created_at,
            )
            for tweet in tweets
        ]
    return list_of_tweets


def get_tweets_text(hashtags, filter_retweets, languages):
    tweets = get_tweets(
        hashtags=hashtags, filter_retweets=filter_retweets, languages=languages
    )
    return [tweet.text for tweet in tweets]


def get_relevant_tweets(hashtags, filter_retweets, languages, target_hashtag):
    tweets = get_tweets(
        hashtags=hashtags, filter_retweets=filter_retweets, languages=languages
    )

    return [
        {
            "key": tweet.id,
            "text": tweet.text,
            "twitter_handle": "@" + tweet.screen_name,
            "username": tweet.username,
            "datetime": tweet.created_at,
        }
        for tweet in tweets
        if target_hashtag.lower() in tweet.text.lower()
    ]


def make_graph(request: GraphRequest):
    corpus = get_tweets_text(
        hashtags=request.hashtags,
        filter_retweets=request.filter_retweets,
        languages=request.languages,
    )
    print("Building the graph...")
    network_builder = NetworkBuilder()
    network_builder.load_clean_corpus(corpus)
    keywords_to_remove = request.hashtags if len(request.hashtags) == 1 else []
    graph = network_builder.build_graph(
        filter_node_frequency=request.filter_node_frequency,
        filter_link_frequency=request.filter_link_frequency,
        keywords_to_remove=keywords_to_remove,
    )
    return graph


@app.post("/get-graph")
async def root(request: GraphRequest):
    print(request)
    return make_graph(request)


@app.post("/get-tweets-for-hashtag")
async def api_get_tweets(request: TweetsRequest):
    tweets = get_relevant_tweets(
        hashtags=request.hashtags,
        filter_retweets=request.filter_retweets,
        languages=request.languages,
        target_hashtag=request.target_hashtag,
    )
    return tweets

