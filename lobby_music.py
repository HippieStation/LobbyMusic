import json
import random
import youtube_dl
import os
import ffmpeg_normalize
import shutil

def load_txt_song_list():
    songs = []
    with open("./lobby_songs.txt") as lobby_songs:
        for song in lobby_songs:
            song = song.strip()
            if song.startswith("#") or song == "":
                continue
            songs.append(song)
    return songs

def load_json_lobby():
    songs = []
    with open("./lobby_songs.json") as lobby_songs_f:
        lobby_songs = lobby_songs_f.read()
        if lobby_songs == "" or lobby_songs == None:
            return {}
        return json.loads(lobby_songs)

def save_json_lobby(db):
    with open("./lobby_songs.json", 'w+') as lobby_songs:
        lobby_songs.write(json.dumps(db, indent=4))

def update_db_counts(songs, db):
    for song in songs:
        db[song]['count'] += 1

def check_database(db, txt):
    print("Removing old DB entries:")
    for (song, data) in db.items():
        if song in txt:
            continue
        else:
            print("\tRemoving {}".format(song))
            del db[song]
    
    print("Syncing text with DB:")
    for song in txt:
        if song in db:
            continue
        else:
            print("\tAdding {} to DB".format(song))
            db[song] = {"count": 0}

def pick_songs(songs_needed, db):
    print("Attempting to pick {} songs".format(songs_needed))
    songs_by_count = {}
    for (song, data) in db.items():
        song_url = song
        count = data['count']
        if count not in songs_by_count:
            songs_by_count[count] = []
        songs_by_count[count].append(song_url)
    songs_by_count = sorted(songs_by_count.items())
    
    chosen_songs = []
    for tup in songs_by_count:
        count = tup[0]
        songs = tup[1]
        random.shuffle(songs)
        for song in songs:
            if len(chosen_songs) == songs_needed:
                break
            chosen_songs.append(song)
        
        if len(chosen_songs) == songs_needed:
                break

    if len(chosen_songs) != songs_needed:
        print("Couldn't get {} songs, only got {}.".format( songs_needed, len(chosen_songs)))

    return chosen_songs

def print_songs(song_list):
    for song in song_list:
        count = db[song]['count']
        print("{} - been the lobby music {} times.".format(song, count))

def clean_dirs():
    for path in ["./lobby_music", "./raw_songs/normalized"]:
        for filename in os.listdir(path):
            filepath = os.path.join(path, filename)
            try:
                shutil.rmtree(filepath)
            except OSError:
                os.remove(filepath)

song_file = "" # Small hack to get the file name from the YouTube downloader
def _download_link(song_url):
    global song_file

    def ydl_hook(d):
        global song_file
        if d['status'] == "finished":
            song_file = d['filename']

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'vorbis',
            'preferredquality': '128',
        }],
        'progress_hooks': [ydl_hook],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([song_url])
    
    song_file, ext = os.path.splitext(song_file)
    song_file = "{}.ogg".format(song_file)
    new_path = "./raw_songs/{}".format(song_file)
    print("Moving {} to {}".format(song_file, new_path))
    shutil.move(song_file, new_path)
    return new_path

def download_song(song, db):
    if "filepath" in db[song]:
        print("Using cached copy of: {}".format(song))
        return db[song]["filepath"]
    else:
        print("Downloading {}".format(song))
        file_path = _download_link(song)
        db[song]["filepath"] = file_path
        return file_path

def normalise_audio(path):
    args =  {
        '--acodec': "libvorbis",
        '--debug': False,
        '--dir': "normalized",
        '--dry-run': False,
        '--ebu': False,
        '--extra-options': "-t 150",
        '--force': False,
        '--format': 'ogg',
        '--level': '-32',
        '--max': False,
        '--merge': False,
        '--no-prefix': False,
        '--prefix': 'normalized',
        '--threshold': '0.5',
        '--verbose': False,
        '<input-file>': [path]
    }

    normaliser = ffmpeg_normalize.FFmpegNormalize(args)
    normaliser.run()
    filename = os.path.basename(path)
    shutil.move("./raw_songs/normalized/{}".format(filename), "./lobby_music/{}".format(filename))
    return "./lobby_music/{}".format(filename)

def process_songs(song_list, db):
    lobby_music = []
    for song in song_list:
        path = download_song(song, db)
        lobby_music.append(normalise_audio(path))
    return lobby_music

def generate_config(paths):
    config = ""
    for path in paths:
        filename = os.path.basename(path)
        config = config + "sounds/lobby_music/{}\n".format(filename)
    config_f = file("./lobby_music/round_start_sounds.txt", 'w+')
    config_f.write(config)
    print("Config written to ./lobby_music/round_start_sounds.txt")

db = load_json_lobby()
txt = load_txt_song_list()

check_database(db, txt)
chosen_songs = pick_songs(6, db)
print_songs(chosen_songs)
clean_dirs()
lobby_music = process_songs(chosen_songs, db)
generate_config(lobby_music)
update_db_counts(chosen_songs, db)
save_json_lobby(db)
print("All done <3")
