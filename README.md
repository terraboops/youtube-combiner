# Description:
This is an interactive terminal application which combines YouTube playlists for you. The OAuth flow used requires you to interactively obtain a token for the app to use and paste it in.

You need to enable YouTube API access on your Google account and get credentials. This script assumes you put your credentials in a file called `client_id.json` in the same directory as the script.

More details:
https://console.cloud.google.com/apis/library/youtube.googleapis.com

## Features:
- Crap code, hacky gotchas, surprises
- Obtain playlists from a Channel by ID or YouTube username
- Filter playlist titles with glob-style pattern (ex: `*2017*`)
- Sorts videos by super well-proven, bullet-proof, industry grade heuristics of radness determination

# Installation:
`pip install -r requirements.txt`

# Usage:
```
usage: youtube.py [-h] (--username USERNAME | --channel CHANNEL)
                  [--matches MATCHES] [--sort] [--debug]
                  [--privacy {public,private,unlisted}] [--title TITLE]
                  [--description DESCRIPTION]

Search a Youtube Channel for Playlists and combine them.

optional arguments:
  -h, --help                          show this help message and exit
  --username USERNAME                 YouTube Username - assumes user has 1 channel
  --channel CHANNEL                   YouTube Channel ID
  --matches MATCHES                   Glob-style filter (ex: *2017*) for playlist names
                                      (default: *)
  --sort                              Sort by raddest videos (most engagement)
  --debug                             Print debug info
  --privacy {public,private,unlisted} Output playlist privacy (default: public)
  --title TITLE                       Output playlist title
  --description DESCRIPTION           Output playlist description
```

# Example Run:
```
$ ./youtube.py --username AmazonWebServices --matches '*re:Invent 2017*' --sort --title "Mega Combined re:Invent 2017" --description "Programmatically created... Sorted by user engagement!" --privacy private
Please visit this URL to authorize this application: <Long Google URL>
Enter the authorization code: <Secret OAuth Code from Google Web Page>
Found 227 playlists for channel 'AmazonWebServices'.
Selected 40 playlists from original set based on filter '*re:Invent 2017*'.
Found 719 playlist items across 40 playlists.
Sorting...........................................................................................................................
..................................................................................................................................
..................................................................................................................................
..................................................................................................................................
..................................................................................................................................
..............................................................................
All sorted.
Created playlist {} - adding videos..............................................................................................
..................................................................................................................................
..................................................................................................................................
..................................................................................................................................
..................................................................................................................................
...........................................................................................................
Your playlist is ready: https://www.youtube.com/playlist?list=PLodHjcJZXgUYhyRcsil3gDTJIiqy-pD4C
```

# TODO - Probably not gonna happen ever tbh
 - [ ] Make all the code not suck (all the kwargs, DRY it up, what are tests?, etc...)
 - [ ] Parallel scoring of videos, because fast
 - [ ] Better dev experience - regenerating the token every time is annoying (sorry)
 - [ ] Why isn't this a web app? Make it so!
 - [ ] Combine arbitrary playlist IDs