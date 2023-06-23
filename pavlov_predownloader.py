import os
import configparser
import requests
import json
import shutil
import zipfile
import re
import sys
from tqdm import tqdm

API_KEY = 'YOUR_MOD.io_API_KEY'


appdata_folder = os.getenv('LOCALAPPDATA')


with open(os.path.join(appdata_folder, "Pavlov", "Saved", "Config", "Windows", "GameUserSettings.ini"), "r") as config:
    for line in config:
        if line.startswith("ModDirectory="):
            mod_dir = line.strip().split('=')[1]
if not mod_dir:
    mod_dir = os.path.join(appdata_folder, "Pavlov", "Saved", "Mods")



pavlov_game_id = "3959"

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

mod_list_file = os.path.join(application_path, "modlist.txt")
print("Looking for mod list file {}".format(mod_list_file))
if not os.path.exists(mod_list_file):
    input("Can't find {}, to loads mods from!".format(mod_list_file))
    raise(FileNotFound(mod_list_file))

with open(mod_list_file, "r") as mlf:
    mods_list_text = mlf.read()

pattern = r"(UGC\d+)"

matches = re.findall(pattern, mods_list_text)

print("Found modlinks")

mod_ugcs = []

for match in matches:
    print(match)
    mod_ugcs.append( match[3:])
    
mod_ugcs = list(set(mod_ugcs))


def download(mod_url, mod_id, taint):
    print("downloading", mod_url, mod_id)
    if os.path.exists(os.path.join(mod_dir, "UGC{}".format(mod_id))):
        shutil.rmtree(os.path.join(mod_dir, "UGC{}".format(mod_id)))
    os.makedirs(os.path.join(mod_dir, "UGC{}".format(mod_id)))
    
    zip_file_path = os.path.join(mod_dir, "UGC{}".format(mod_id), "temp.zip")
    
    
    headers = {
            "User-Agent": "Pavlov Mod Updater"
        }
    response = requests.get(mod_url, stream=True, headers=headers)
    total_size = int(response.headers.get('Content-Length', 0))

    # Set up the progress bar
    progress_bar = tqdm(total=total_size, unit='B', unit_scale=True)

    # Download the file with progress
    with open(zip_file_path, 'wb') as file:
        for data in response.iter_content(chunk_size=1024):
            progress_bar.update(len(data))
            file.write(data)

    progress_bar.close()
    
        
    extract_path = os.path.join(mod_dir, "UGC{}".format(mod_id), "Data")
    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)
        
    with open(os.path.join(mod_dir, "UGC{}".format(mod_id), "taint"), "w") as taint_f:
        taint_f.write(str(taint))
    os.remove(zip_file_path)
        


for mod_id in tqdm(mod_ugcs, desc='downloading mods'):
    
    url = "https://api.mod.io/v1/games/{}/mods/{}/files?api_key={}".format(pavlov_game_id, mod_id, API_KEY)

    headers = {
        "X-Modio-Platform": "Windows",
        "User-Agent": "Pavlov Mod Updater"
    }

    response = requests.get(url, headers=headers)
    try:
        mod_url = json.loads(response.content.decode('utf-8'))['data'][0]['download']['binary_url']
    except KeyError:
        print("Mod {}, doesn't exist on mod.io, skipping".format(mod_id))
        continue
        
    taint = mod_url.split('/')[-2]
    
    if os.path.exists(os.path.join(mod_dir, "UGC{}".format(mod_id))):
        try:
            with open(os.path.join(mod_dir, "UGC{}".format(mod_id), "taint"), 'r') as taint_ex:
                if taint_ex.read().strip() != taint:
                    print("Mod {} exists, but old, replacing!".format(mod_id))
                    download(mod_url, mod_id, taint)
                else:
                    print("Mod {} exists and is up to date, skipping!".format(mod_id))
        except FileNotFoundError:
            print("Mod {} exists, but seems to be corrupted, replacing!".format(mod_id))
            download(mod_url, mod_id, taint)
    else:
        download(mod_url, mod_id, taint)

input("Done, you can close this window")

