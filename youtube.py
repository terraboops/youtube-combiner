#!/usr/bin/env python
import os
import argparse
import sys
import fnmatch
import itertools
import time
import math
from functools import partial
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret.
CLIENT_SECRETS_FILE = "client_id.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'


###############################################
###############################################
################### HELPERS ###################
###############################################
###############################################

def get_cli_input():
  parser = argparse.ArgumentParser(description='Search a Youtube Channel for Playlists and combine them.')
  yt_chan_grp = parser.add_mutually_exclusive_group(required=True)
  yt_chan_grp.add_argument('--username', help='YouTube Username - assumes user has 1 channel')
  yt_chan_grp.add_argument('--channel', help='YouTube Channel ID')
  parser.add_argument('--matches', help="Glob-style filter (ex: *2017*) for playlist names (default: *)", default="*")
  parser.add_argument('--sort', help="Sort by raddest videos (most engagement)", action='store_true')
  parser.add_argument('--debug', help="Print debug info", action='store_true')
  parser.add_argument('--privacy', help="Output playlist privacy", default="public", choices=['public', 'private', 'unlisted'])
  parser.add_argument('--title', help="Output playlist title", default="YouTube Combiner Playlist Output")
  parser.add_argument('--description', help="Output playlist description", default="ITS A PLAYLIST OF PLAYLISTS!!!111")
  return parser

# The remaining helpers are used in Google's example code
def get_authenticated_service():
  flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
  credentials = flow.run_console()
  return build(API_SERVICE_NAME, API_VERSION, credentials = credentials)

# Build a resource based on a list of properties given as key-value pairs.
# Leave properties with empty values out of the inserted resource.
def build_resource(properties):
  resource = {}
  for p in properties:
    # Given a key like "snippet.title", split into "snippet" and "title", where
    # "snippet" will be an object and "title" will be a property in that object.
    prop_array = p.split('.')
    ref = resource
    for pa in range(0, len(prop_array)):
      is_array = False
      key = prop_array[pa]

      # For properties that have array values, convert a name like
      # "snippet.tags[]" to snippet.tags, and set a flag to handle
      # the value as an array.
      if key[-2:] == '[]':
        key = key[0:len(key)-2:]
        is_array = True

      if pa == (len(prop_array) - 1):
        # Leave properties without values out of inserted resource.
        if properties[p]:
          if is_array:
            ref[key] = properties[p].split(',')
          else:
            ref[key] = properties[p]
      elif key not in ref:
        # For example, the property is "snippet.title", but the resource does
        # not yet have a "snippet" object. Create the snippet object here.
        # Setting "ref = ref[key]" means that in the next time through the
        # "for pa in range ..." loop, we will be setting a property in the
        # resource's "snippet" object.
        ref[key] = {}
        ref = ref[key]
      else:
        # For example, the property is "snippet.description", and the resource
        # already has a "snippet" object.
        ref = ref[key]
  return resource

# Remove keyword arguments that are not set
def remove_empty_kwargs(**kwargs):
  good_kwargs = {}
  if kwargs is not None:
    for key, value in kwargs.iteritems():
      if value:
        good_kwargs[key] = value
  return good_kwargs

###############################################
###############################################
############### YOUTUBE METHODS ###############
###############################################
###############################################

def channels_list_by_username(client, **kwargs):
  kwargs = remove_empty_kwargs(**kwargs)

  response = client.channels().list(
    **kwargs
  ).execute()

  return next(iter(response['items']), None)

def recurse_playlists_list_by_channel_id(client, **kwargs):
  kwargs = remove_empty_kwargs(**kwargs)

  response = client.playlists().list(
    **kwargs
  ).execute()

  # more items - recurse
  if 'nextPageToken' in response:
    kwargs['pageToken'] = response['nextPageToken']
    response['items'] = response['items'] + recurse_playlists_list_by_channel_id(client, **kwargs)

  # no more items - return items
  return response['items']

def recurse_playlist_items_list_by_playlist_id(client, **kwargs):
  kwargs = remove_empty_kwargs(**kwargs)

  response = client.playlistItems().list(
    **kwargs
  ).execute()

  # more items - recurse
  if 'nextPageToken' in response:
    kwargs['pageToken'] = response['nextPageToken']
    response['items'] = response['items'] + recurse_playlist_items_list_by_playlist_id(client, **kwargs)

  # no more items - return items
  return response['items']

def videos_list_by_id(client, **kwargs):
  kwargs = remove_empty_kwargs(**kwargs)

  response = client.videos().list(
    **kwargs
  ).execute()

  return response['items']

def get_video_score(client, video_id):
  video_details = next(iter(videos_list_by_id(client, part='statistics,snippet', id=video_id)),None)
  if video_details:
    stats = video_details['statistics']
    # sum engagement counts according to some heuristics I made up
    return sum((
      int(stats.get('viewCount',0)),
      int(stats.get('dislikeCount',0)), # even bad publicity is good publicity!
      int(stats.get('commentCount',0)) * 10,
      int(stats.get('likeCount',0)) * 100,
      int(stats.get('favoriteCount',0)) * 1000
    ))

def playlists_insert(client, properties, **kwargs):
  resource = build_resource(properties)
  kwargs = remove_empty_kwargs(**kwargs)

  response = client.playlists().insert(
    body=resource,
    **kwargs
  ).execute()

  return response

# Crappy exception handling - because we need it to work
def playlist_items_insert(client, properties, **kwargs):
  resource = build_resource(properties)
  kwargs = remove_empty_kwargs(**kwargs)

  try:
    response = client.playlistItems().insert(
      body=resource,
      **kwargs
    ).execute()
  except Exception as e:
    if args.debug:
      print(str(e))
    return None

  return response

# Performs a glob-style match on playlist string given filter pattern
def playlist_name_matches(playlist, filter):
  return fnmatch.fnmatch(playlist['snippet']['title'], filter)

if __name__ == '__main__':

  args = get_cli_input().parse_args()
  if args.debug:
    print(vars(args))

  os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
  client = get_authenticated_service()

  if args.username:
    channel = channels_list_by_username(client,
      part='id',
      forUsername=args.username)

    if channel is None:
      print('Unable to find requested channel.')
      sys.exit(1)
  else:
    channel = { 'id': args.channel }

  all_playlists_for_channel = recurse_playlists_list_by_channel_id(client,
    part='contentDetails,snippet',
    channelId=channel['id'],
    maxResults=50)
  print("Found {} playlists for channel '{}'.".format(len(all_playlists_for_channel), args.username or args.channel))

  filtered_playlists = [playlist for playlist in all_playlists_for_channel if playlist_name_matches(playlist, args.matches)]
  print("Selected {} playlists from original set based on filter '{}'.".format(len(filtered_playlists), args.matches))

  # Get list of videos for each playlist and flatmap list of lists while removing duplicates
  all_playlist_items = {playlist_item['contentDetails']['videoId']: playlist_item for playlist_items in 
                          [recurse_playlist_items_list_by_playlist_id(client, playlistId=playlist['id'], maxResults=50, part='contentDetails') for playlist in filtered_playlists]
                          for playlist_item in playlist_items}.values()
  print("Found {} playlist items across {} playlists.".format(len(all_playlist_items), len(filtered_playlists)))
  
  if args.sort:
    sys.stdout.write("\rSorting.")
    sys.stdout.flush()
    for playlist_item in all_playlist_items:
      # TODO - Parallelize this
      playlist_item['score'] = get_video_score(client, playlist_item['contentDetails']['videoId'])
      if args.debug:
        print("Scored {} as {}.".format(playlist_item['contentDetails']['videoId'], playlist_item['score']))
      else:
        sys.stdout.write(".")
        sys.stdout.flush()
    sys.stdout.write(".\n")
    sys.stdout.flush()

    all_playlist_items.sort(key=lambda item: item['score'], reverse=True)
    print('All sorted.')

  created_playlist = playlists_insert(client, 
    {
      'snippet.title': args.title,
      'snippet.description': args.description,
      'status.privacyStatus': args.privacy
    },
    part='snippet,status')
  
  if 'id' in created_playlist:
    sys.stdout.write("\rCreated playlist {} - adding videos."),
    sys.stdout.flush()

    for playlist_item in all_playlist_items:
      playlist_item_res = {
        'snippet.playlistId': created_playlist['id'],
        'snippet.resourceId.kind': 'youtube#video',
        'snippet.resourceId.videoId': playlist_item['contentDetails']['videoId'],
        'snippet.position': ''
      }
      attempts = 0
      sys.stdout.write(".")
      sys.stdout.flush()
      while(playlist_items_insert(client, playlist_item_res, part='snippet') is None):
        sys.stdout.write(".")
        sys.stdout.flush()
        attempts += 1
        if attempts > 4:
          print('\n\rGiving up on item {}.\n\r'.format(playlist_item['contentDetails']['videoId']))
          if args.debug:
            print playlist_item_res
          break
        if args.debug:
          print('Failed to add item {} - sleeping {} seconds.'.format(playlist_item['contentDetails']['videoId'],math.pow(attempts,attempts)))
        time.sleep(math.pow(attempts,attempts))
      if args.debug:
        print('Added item {}.'.format(playlist_item['contentDetails']['videoId']))
    sys.stdout.write(".\n")
    sys.stdout.flush()
    print('Your playlist is ready: https://www.youtube.com/playlist?list={}'.format(created_playlist['id']))
  else:
    print('Unable to create playlist!')
