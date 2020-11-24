from flask import Flask, render_template, url_for, jsonify, request
import os
import os.path
import json
import base64
import requests
from mutagen.mp3 import MP3
import math

app = Flask(__name__)

@app.route('/get_library')
def index():
  def get_file_structure():
    audiobook_authors_path = "/mnt/plexmedia/Audiobooks"

    audiobook_dict = {}

    author_dirpath, author_dirnames, author_filenames = next(os.walk(audiobook_authors_path))
    for author_dirname in author_dirnames:

      audiobook_dict[author_dirname] = {}

      audiobook_book_path = os.path.join(author_dirpath, author_dirname)
      book_dirpath, book_dirnames, book_filenames = next(os.walk(audiobook_book_path))

      for book_dirname in book_dirnames:
        audiobook_dict[author_dirname][book_dirname] = []

        audiobook_track_path = os.path.join(book_dirpath, book_dirname)
        track_dirpath, track_dirnames, track_filenames = next(os.walk(audiobook_track_path))
        track_filenames.sort()

        for track_filename in track_filenames:
          try:
            # Commenting out for now as it takes a long time to run
            # track_length_seconds = round(MP3(os.path.join(track_dirpath, track_filename)).info.length)
            track_length_seconds = 200 # PLACEHOLDER
          except:
            track_length_seconds = -1

          track_length = f"{math.floor(track_length_seconds / 60)}min {track_length_seconds % 60}sec"

          track_dict = {
            "track_filename": track_filename,
            "track_length": track_length
          }

          # print(track_dict)

          audiobook_dict[author_dirname][book_dirname].append(track_dict)


    return audiobook_dict

  return jsonify(get_file_structure())


@app.route('/')
def default():
  return "API running"

@app.route('/set_current_track', methods=['POST'])
def set_track():
  decoded_value = request.data.decode('utf-8')
  json_value = json.loads(decoded_value)
  json_prettified = json.dumps(json_value, indent=2)  

  with open("db/current_track.json", "w") as f:
    f.write(json_prettified)
    return "success"

@app.route('/get_current_track')
def get_track_json():
  with open("db/current_track.json", "r") as f:
    data = json.load(f)
    return data




if __name__ == "__main__":
  app.run(debug=True, host= '0.0.0.0', port=5200)


