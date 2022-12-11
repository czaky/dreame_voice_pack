# Script to generate Dreame robot voice-packs using uberduck.ai TTS.

import errno
import os
import shutil
import signal
import argparse
from subprocess import call, run

import re
import csv
import hashlib
from pathlib import Path
from typing import Dict

from uberduck import UberDuck

# Return a hash string for the THING 
def hash(thing) -> str:
    return hashlib.md5(str(thing).encode('utf-8')).hexdigest()

# Used to timeout TTS API calls
class TimeoutError(Exception):
    pass

# TTS API initialization error.
class MissingTextToSpeechServerError(Exception):
    pass

# Interacts with the Uberduck.AI API.
class TTS():
    DEFAULT_TIMEOUT = 20

    # Initialize providing the keys and the voice
    def __init__(self, pub, pk, voice, timeout = None):
        self.pub = pub
        self.pk = pk
        self.voice = voice
        self.timeout = timeout if timeout else TTS.DEFAULT_TIMEOUT
        self.api = None

    # Returns True if we could connect to Uberduck using the keys.
    def connect(self):
        try:
            self.api = UberDuck(self.pub, self.pk)
            if self.api: return True
        except Exception as e:
            print(f"Could not connect to UberDuck using {self.pub} and {self.pk}.")
        return False

    # Transform the text into an output audio file.
    #
    # Return True on success.
    def transform(self, text, output, timeout):
        if len(text) == 0: 
            print(f"Text for {output} is empty.")
            return False
        try:   
            tmp = f"{output}.tmp"     
            if os.path.exists(tmp): os.remove(tmp)
            result = self._get_audio(text, file_path = tmp, timeout = timeout)
            if result:
                os.replace(tmp, output)
                return True
        except Exception as e:
            print(f"Exception while transforming {output}: {e}.")
            self.api = None

        return False

    def _on_timeout(self, signum, frame):
        raise TimeoutError('Uberduck.AI timed out.')

    # Get audio but make sure we timeout if it taks too long.
    def _get_audio(self, text, file_path, timeout = None):
        if self.api is None and not self.connect(): return False

        signal.signal(signal.SIGALRM, self._on_timeout)
        try:
            signal.alarm(timeout if timeout else self.timeout)
            result = self.api.speak(text, self.voice, file_path = file_path)
        finally:
            signal.alarm(0)
        return result
        
# Reads the configs, sayings, and transforms the sayings' text to a voice pack.
class Generator():

    DEFAULT_VOICE = 'glados' 
    DEFAULT_DIR = Path("default/")

    # Initializes the generator for the given uberduck.ai voice target.
    #
    # volume - is passed to ffmpeg to change the volume of the resulting TTS speech
    # normalize - flag that enables calling ffmpeg-normalize on the TTS output
    # timeout - the default timeout used for the TTS API
    def __init__(self, voice = None, 
                volume = None, normalize = False,
                timeout = None):
        if voice is None: voice = Generator.DEFAULT_VOICE
        if timeout is None: timeout = TTS.DEFAULT_TIMEOUT
        self.voice = str(voice).strip().lower()
        self.dir = Path(f"{voice}/")
        self.volume = volume
        self.normalize = normalize
        self.timeout = timeout

        keys = self.load_keys("keys.csv")
        #print(keys)
        all_tts = [TTS(pub, pk, voice = self.voice, timeout = self.timeout) for pub,pk in keys]
        self.tts = [tts for tts in all_tts if tts.connect()]

        if len(self.tts) == 0:
            raise MissingTextToSpeechServerError("No usable TTS keys found. Aborting voice generation.")
            
        default_replacements = self.load_replacements(Generator.DEFAULT_DIR / "replacement.csv")
        raw_replacements = self.load_replacements(self.dir / "replacement.csv", default_replacements)
        # print(raw_replacements)
        self.replacements = self.prepare_replacements(raw_replacements)
        # print(self.replacements)

        default_sayings = self.load_sayings(Generator.DEFAULT_DIR / "sayings.csv")
        self.sayings = self.load_sayings(self.dir / "sayings.csv", default_sayings)

    # Loads the TTS API keys from the provided file.
    def load_keys(self, filepath) -> list:
        data = []
        line = 0
        with open(filepath) as file:
            for row in csv.reader(file, skipinitialspace=True):
                line += 1
                if len(row) == 0: continue
                if len(row) == 1 and len(str(row[0]).strip()) == 0: continue
                if len(row) != 2 or len(str(row[0]).strip()) == 0 or len(str(row[1]).strip()) == 0:
                    row_str = "','".join(row)
                    print(f"ERROR: Need two keys (pub, pk) in line [{filepath}:{line}] '{row_str}'")
                    continue
                data.append(row)
        return data

    # Loads text replacements from the given file. 
    def load_replacements(self, filepath, data = {}) -> Dict[str, str]:
        if not os.path.exists(filepath): return data 
        line = 0
        with open(filepath) as file:
            for row in csv.reader(file, skipinitialspace=True):
                line += 1
                if len(row) == 0: continue
                if len(row) == 1 and len(str(row[0]).strip()) == 0: continue
                if len(row) != 2 or len(str(row[0]).strip()) == 0 or len(str(row[1]).strip()) == 0:
                    row_str = "','".join(row)
                    print(f"ERROR: Need before and after strings for replacement [{filepath}:{line}] '{row_str}'")
                    continue
                data[str(row[0]).strip().lower()] = str(row[1]).strip().lower()
        return data

    # Compiles the replacements as regular expressions.
    def prepare_replacements(self, replacements):
        result = []
        for search, replace in replacements.items():
            result.append((re.compile(f"\\b{search}\\b"), replace))
        return result
        
    # Applies the replacements to the text in a serial manner.
    def apply_replacements(self, text):
        for search, replace in self.replacements:
            text = re.sub(search, replace, text)
        return text

    # Loads and normalizes the text for each robot saying. Returns a dictionary.
    def load_sayings(self, filepath, data = {}) -> Dict[int, str]:
        if not os.path.exists(filepath): return data 
        line = 0
        with open(filepath) as file:
            for row in csv.reader(file, skipinitialspace=True):
                line += 1
                if len(row) == 0: continue
                if len(row) == 1 and len(str(row[0]).strip()) == 0: continue
                if len(row) != 2 or len(str(row[0]).strip()) == 0:
                    row_str = "','".join(row)
                    print(f"ERROR: Need a number and a text for the saying: [{filepath}:{line}] '{row_str}'")
                    continue
                try:
                    id = int(row[0])
                    text = self.apply_replacements(str(row[1]).strip().lower())
                    data[id] = text
                except Exception as e:
                    row_str = "','".join(row)
                    print(f"Error in line [{filepath}:{line}] '{row_str}' ...\n {e}")
                    continue
        return data

    # Applies some transformations on the TTS audio like ffmpeg-normalize
    def process_audio(self, input, output):
        audio = input
        if self.volume:
            tmp = f"{output}.tmp.{Path(output).suffix}"
            if os.path.exists(tmp): os.remove(tmp)
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", 
                "-i", str(audio), "-filter:a", f"volume={self.volume}", str(tmp)])
            os.replace(tmp, output)
            audio = output
        if self.normalize:
            # Why do we have this lever?
            run(["ffmpeg-normalize", "-q",  "-o", str(output), "-f", str(audio)])
            audio = output
        return audio

    # Converts the audio to the vorbis OGG format.
    def convert_to_ogg(self, input, output):
        run(["oggenc", str(input), "--output", str(output), "--bitrate", "100", "--resample", "16000", "-Q"])

    # Iterates through all the sayings, uses TTS and then normalizes audio if necessary.
    def process(self):
        default_dir = Path("default/")
        voice_dir = Path(f"{self.voice}/")
        if not os.path.exists(voice_dir): os.mkdir(voice_dir)
        tts_dir = voice_dir / "tts/"
        if not os.path.exists(tts_dir): os.mkdir(tts_dir)
        ogg_dir = voice_dir / "ogg/"
        if not os.path.exists(ogg_dir): os.mkdir(ogg_dir)

        items = [] 
        for id, text in self.sayings.items():
            items.append((id, text, self.timeout))

        files = []
        tts_index = 0
        while len(items) > 0:
            id, text, timeout = items.pop(0)
            ogg_path = ogg_dir / f"{id}.ogg"
            print(f"Processing {ogg_path}: \"{text}\"")

            if len(text) == 0:
                default = voice_dir / f"{id}.ogg"
                if not os.path.exists(default):     
                    default = default_dir / f"{id}.ogg"
                if os.path.exists(default):
                    print(f"Reusing: {default}")
                    shutil.copy(default, ogg_path)
                    files.append(ogg_path.name)
                    continue

                print(f"WARNING: No default found for {ogg_path}: \"<empty-text>\"")
                continue

            md5 = hash(text)
            tts_path = tts_dir / f"{md5}.wav"
            
            if not os.path.exists(tts_path):
                tts_index += 1
                tts_index %= len(self.tts)
                # Transform text to speech
                if not self.tts[tts_index].transform(text, tts_path, timeout):
                    # On failure, reschedule the transform with more timeout.
                    items.append((id, text, round((2 + timeout) * 1.5) ))
                    continue
            
            tmp_path = tts_dir / f"{md5}-processed.wav"
            processed = self.process_audio(tts_path, tmp_path)
            self.convert_to_ogg(processed, ogg_path)
            files.append(ogg_path.name)

        # Generate the archive.
        run(["tar", "-c", "-z", "-f", "../voice.tar.gz", *files], cwd = ogg_dir)
        # Generate the MD5 sum and store it in HASH.txt.
        with open(voice_dir / "HASH.txt", "w") as file:
            run(["md5sum", "--tag", "-b", "voice.tar.gz"], stdout= file, cwd = voice_dir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Dreame Voice Pack')
    parser.add_argument('--voice', default = Generator.DEFAULT_VOICE)
    parser.add_argument('--volume', default = None, 
                        help='Volume parameter passed to ffmpeg as factor or db.')
    parser.add_argument('--timeout', default = TTS.DEFAULT_TIMEOUT, type=int, 
                        help='Timeout to be used with the TTS API.')
    parser.add_argument('--normalize', action='store_true', 
                        help='Normalize the sound. Not recommended.')
    args = parser.parse_args()

    # print(args)
    g = Generator(
            args.voice, 
            volume = args.volume, 
            normalize = args.normalize, 
            timeout = args.timeout)

    g.process()