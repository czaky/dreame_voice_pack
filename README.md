# Voice Packs for Dreame Vacuum Robots

Uses voice generation by [Uberduck.AI](https://uberduck.ai/).

Works at least with `L10s Ultra`, `L10 Pro`, `Z10 Pro` and `W10`.
Optimized for [valetudo](https://valetudo.cloud/) use.

Current voice packs:
 
  * [GLaDOS voice pack](./glados/voice.tar.gz) - [hash code](./glados/HASH.txt)
  * [Tiff voice pack](./kirby-tiff/voice.tar.gz) - [hash code](./kirby-tiff/HASH.txt)
  * [Sweetie voice pack](./sweetie-belle/voice.tar.gz) - [hash code](./sweetie-belle/HASH.txt)

## Installation

1. In Valetudo go to "Robot Settings" -> "Misc Settings"
2. Enter the following information in the "Voice packs" section:
    - URL: https://github.com/czaky/dreame_voice_pack/raw/master/\<character\>/voice.tar.gz
        - for example: https://github.com/czaky/dreame_voice_pack/raw/master/glados/voice.tar.gz  
    - Language Code: `CUSTOM` - or anything but language codes like `EN`
        - for example: `GLADOS`
    - Hash: Lookup in the \<character\>/`HASH.txt` file
        - for example: `bc10b417ace1dd1aaf4f3e1525aa3b73`
3. Click "Set Voice Pack"

4. Check if the `*.ogg` files have been copied to `/data/personalized_voice/CUSTOM/` directory on the robot.
5. If not, extract the `voice.tar.gz` and copy the `*.ogg` files using your favorite `scp` tool. 

## Generation

### Prerequisites

1. Install `ffmpeg` and `vorbis-tools`

```sh
sudo apt install ffmpeg vorbis-tools
```

2. Install uberduck python API and ffmpeg-normalize

```sh
pip install uberduck ffmpeg-normalize
```

### Invocation

1. Sing up with https://uberduck.ai
2. Generate a public key and a secret token in your profile.
3. Replace the public keys and tokens in the `keys.csv`
4. Run the script (replacing `kirby-tiff` with one of the voices)

```sh
python generate.py --voice kirby-tiff [--volume 1.1] [--normalize]
```

The default voice is `glados`.

Note: Normalization uses `ffmpeg` and may create random artifacts in the resulting audio. It is not recommended with Uberduck.AI voice characters.  

Note: voice list can be found at https://app.uberduck.ai/quack-help . 
Not all voices are good. Please, consult: https://app.uberduck.ai/leaderboard/voice

Listen to the resulting `.ogg` files for any artifacts. Change the text if necessary.

### Modify

The defaults are loaded first and are found in the `defaults` folder.
Then the values in each character folder override the defaults.
Each folder can have following files:

 * `./sayings.csv` - a list of saying IDs and saying texts. If the text is empty, generator will look for a prepared `.ogg` file.
 * `./replacement.csv` - a list of words and their replacements, in case the AI characters cannot pronounce those correctly.
 * `./*.ogg` - prepared ogg audio files, used when the text for the saying ID is empty.

### Results

In each voice-character folder:

 * `./voice.tar.gz` - archive of the voices generated.
 * `./HASH.txt` - contains the md5 hash code of the voice archive.
 * `./ogg/*.ogg` - resulting ogg audio files, that go into the archive.
 * `./tts/*.wav` - transformed text audios with name being the hash of the text.

## Contribute

Please, don't add any obscenity or racist stuff. We cannot accept this on a public directory. There is no point in offending anybody. Reserve this stuff for your local installation.

Also, please, don't add anything copy-protected.

## Thanks

Thanks to https://github.com/ccoors/dreame_voice_packs and https://github.com/Findus23/voice_pack_dreame for the inspiration and https://uberduck.ai for the voice generation.
