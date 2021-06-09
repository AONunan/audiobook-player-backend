from flask import Flask, render_template, url_for, jsonify, request
import os
import json
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
import math
import re
import requests
import urllib.parse
import time

app = Flask(__name__)

@app.route('/trigger_library_scan')
def trigger_library_scan():
  def prettify_time(time, round_to="minutes"):

    if round_to == "minutes":
      time_hours = math.floor(time/3600)
      time = time - time_hours*3600

      time_minutes = round(time/60)

      if time_hours == 0:
        time_string = f"{time_minutes} min"
      else:
        time_string = f"{time_hours} hr {time_minutes} min"

    elif round_to == "hours":
      time_string = round(time/3600)

    return time_string

  with open("db/library.json", "r") as f:
    library_old = json.load(f)
  
  return_message_books_added = []

  audiobook_authors_path = "/mnt/plexmedia/Audiobooks"

  audiobook_dict = {}

  author_dirpath, author_dirnames, author_filenames = next(os.walk(audiobook_authors_path))
  author_dirnames.sort()

  for author_dirname in author_dirnames:
  # for author_dirname in [author_dirnames[1]]:

    audiobook_dict[author_dirname] = {}

    audiobook_book_path = os.path.join(author_dirpath, author_dirname)
    book_dirpath, book_dirnames, book_filenames = next(os.walk(audiobook_book_path))
    book_dirnames.sort()

    for book_dirname in book_dirnames:

      # If the book DOESN'T already exist in the library, then display the newly added book
      if not ((author_dirname in library_old) and (book_dirname in library_old[author_dirname])):
        return_message_books_added.append(f"{author_dirname}/{book_dirname}")

      book_length_seconds = 0
      book_file_size_bytes = 0
      book_tracks = {}

      audiobook_track_path = os.path.join(book_dirpath, book_dirname)
      track_dirpath, track_dirnames, track_filenames = next(os.walk(audiobook_track_path))
      track_filenames.sort()

      track_number = 1

      for track_filename in track_filenames:
        track_full_path = os.path.join(track_dirpath, track_filename)
        
        if(track_full_path.endswith(".mp3") or track_full_path.endswith(".m4a") or track_full_path.endswith(".m4b")):
          book_file_size_bytes += os.path.getsize(track_full_path)
        
        try:
          # Attempt to read the track length from the old library JSON
          track_length_seconds = library_old[author_dirname][book_dirname]["tracks"][track_filename]["track_length_seconds"]
        except:
          # If the track length didn't exist in the old library JSON, then read the track length directly
          try:
            if(track_full_path.endswith(".mp3")):
              track_length_seconds = round(MP3(track_full_path).info.length)
            elif(track_full_path.endswith(".m4a")):
              track_length_seconds = round(MP4(track_full_path).info.length)
            elif(track_full_path.endswith(".m4b")):
              track_length_seconds = round(MP4(track_full_path).info.length)
            else:
              track_length_seconds = 0

          except:
            track_length_seconds = 0


        book_length_seconds += track_length_seconds

        book_tracks[track_filename] = {}
        book_tracks[track_filename]["track_length"] = prettify_time(track_length_seconds)
        book_tracks[track_filename]["track_length_seconds"] = track_length_seconds
        book_tracks[track_filename]["track_number"] = track_number
        
        track_number += 1

      title_search = re.search('(\d\d\d\d) - (.*) \((.*)\)', book_dirname)

      year = int(title_search.group(1))
      book_title = title_search.group(2)
      narrator = title_search.group(3)

      audiobook_dict[author_dirname][book_dirname] = {
        "year": year,
        "book_title": book_title,
        "narrator": narrator,
        "book_length": prettify_time(book_length_seconds, round_to="hours"),
        "book_length_seconds": book_length_seconds,
        "book_file_size_bytes": book_file_size_bytes,
        "book_file_size_MB": round(book_file_size_bytes/1024/1024),
        "tracks": book_tracks,
      }

      # Get book cover

      cover_image_file = f"../audiobook-player-frontend/static/cover_images/{author_dirname}_{book_dirname}.jpg"

      # Check if the cover file DOESN'T exist
      if not (os.path.isfile(cover_image_file)):
        open_library_search_url = f"http://openlibrary.org/search.json?author={urllib.parse.quote(author_dirname)}&title={urllib.parse.quote(book_title)}"
        print(f"Searching for book: {open_library_search_url}")
        response = requests.get(open_library_search_url)
        response_body = response.json()

        download_generic_cover_image = False

        if(response_body["numFound"] > 0):
          cover_edition_key_found = False

          for book_result in response_body["docs"]:
            if("cover_edition_key" in book_result):
              print("Found cover edition key")
              cover_edition_key_found = True

              open_library_cover_edition_key = book_result["cover_edition_key"]
              open_library_cover_url = f"http://covers.openlibrary.org/b/olid/{open_library_cover_edition_key}-L.jpg"
              print(f"Searching for cover image: {open_library_cover_url}")

              image_response = requests.get(open_library_cover_url)

              with open(cover_image_file, 'wb') as f:
                f.write(image_response.content)

              break

          if(cover_edition_key_found == False):
            download_generic_cover_image = True
            print("Cover edition key not found, skipping")
            
        else:
          download_generic_cover_image = True
          print(f"No results found for: {open_library_search_url}")

        if(download_generic_cover_image):
          print("Downloading generic cover image")
          print()

          with open(cover_image_file, 'wb') as f:
            f.write(requests.get("https://memegenerator.net/img/images/16143029/generic-book-cover.jpg").content)


  with open("db/library.json", "w") as f:
    f.write(json.dumps(audiobook_dict, indent = 2))

    # return return_message
    return render_template(
      'scan_complete.html',
      return_message_books_added=return_message_books_added,
      # return_message_books_added=["hello there", "this is a test", "testing123"]
    )
  

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


