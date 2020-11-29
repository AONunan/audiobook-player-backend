from flask import Flask, render_template, url_for, jsonify, request
import os
import os.path
import json
import base64
import requests
from mutagen.mp3 import MP3
import math
import re

app = Flask(__name__)

@app.route('/trigger_library_scan')
def trigger_library_scan():
  def prettify_time(time):
    time_hours = math.floor(time/3600)
    time = time - time_hours*3600

    time_minutes = round(time/60)
    # time = time - time_minutes*60

    time_seconds = time

    if time_hours == 0:
      time_string = f"{time_minutes}min"
    else:
      time_string = f"{time_hours}hr {time_minutes}min"

    return time_string

  audiobook_authors_path = "/mnt/plexmedia/Audiobooks"

  audiobook_dict = {}

  author_dirpath, author_dirnames, author_filenames = next(os.walk(audiobook_authors_path))
  author_dirnames.sort()

  for author_dirname in author_dirnames:

    audiobook_dict[author_dirname] = {}

    audiobook_book_path = os.path.join(author_dirpath, author_dirname)
    book_dirpath, book_dirnames, book_filenames = next(os.walk(audiobook_book_path))
    book_dirnames.sort()

    for book_dirname in book_dirnames:

      book_length_seconds = 0
      book_tracks = []

      audiobook_track_path = os.path.join(book_dirpath, book_dirname)
      track_dirpath, track_dirnames, track_filenames = next(os.walk(audiobook_track_path))
      track_filenames.sort()

      for track_filename in track_filenames:
        try:
          track_length_seconds = round(MP3(os.path.join(track_dirpath, track_filename)).info.length)
          book_length_seconds += track_length_seconds
        except:
          track_length_seconds = -1

        track_dict = {
          "track_filename": track_filename,
          "track_length": prettify_time(track_length_seconds),
          "track_length_seconds": track_length_seconds
        }

        book_tracks.append(track_dict)

      title_search = re.search('(\d\d\d\d) - (.*) \((.*)\)', book_dirname)

      audiobook_dict[author_dirname][book_dirname] = {
        "year": int(title_search.group(1)),
        "book_title": title_search.group(2),
        "narrator": title_search.group(3),
        "book_length": prettify_time(book_length_seconds),
        "book_length_seconds": book_length_seconds,
        "tracks": book_tracks
      }

      sum_of_seconds = 0
      track_number = 0

      for track in audiobook_dict[author_dirname][book_dirname]["tracks"]:
        track["track_number"] = track_number
        track_number += 1

        percentage_complete = round((sum_of_seconds / book_length_seconds) * 100)
        print(percentage_complete)
        sum_of_seconds += track["track_length_seconds"]

        track["percentage_of_book_completed"] = percentage_complete

  with open("db/library.json", "w") as f:
    f.write(json.dumps(audiobook_dict, indent = 2))

    return "Library scan complete"
  

@app.route('/get_library')
def get_library():
  with open("db/library.json", "r") as f:
    data = json.load(f)
    return data


@app.route('/')
def default():
  return "API running"

@app.route('/set_current_track', methods=['POST'])
def set_current_track():
  decoded_value = request.data.decode('utf-8')
  json_value = json.loads(decoded_value)
  json_prettified = json.dumps(json_value, indent=2)  

  with open("db/current_track.json", "w") as f:
    f.write(json_prettified)
    return "success"

@app.route('/get_current_track')
def get_current_track():
  json_file = "db/current_track.json"

  if (os.path.getsize(json_file)):  
    with open(json_file, "r") as f:
      data = json.load(f)
      return data
  else:
    return json.dumps({})




if __name__ == "__main__":
  app.run(debug=True, host= '0.0.0.0', port=5200)


