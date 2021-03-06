# ![MediaForge](media/banner.png)

[![MediaForge Discord](https://discordapp.com/api/guilds/803788965215338546/embed.png)](https://discord.gg/xwWjgyVqBz)
![Total Lines](https://img.shields.io/tokei/lines/github/HexCodeFFF/captionbot)
![Downloads](https://img.shields.io/github/downloads/HexCodeFFF/captionbot/total)
![discord.py](https://img.shields.io/github/pipenv/locked/dependency-version/hexcodefff/captionbot/discord.py)
![python](https://img.shields.io/github/pipenv/locked/python-version/hexcodefff/captionbot)

### A Discord bot for editing and creating videos, images, GIFs, and more!

## general technical info about the bot

- inspired by [esmBot](https://github.com/esmBot/esmBot)
- uses discord.py (python discord lib)
- uses FFmpeg for most media functions
- uses selenium and ChromeDriver to render captions in html with Chrome
    - although not the fastest approach, it is very readable, flexible, and easy to work with/expand.

## to self-host

verified working on windows 10 and ubuntu 18.04

### external libraries

the bot uses many CLI programs for media processing.

- FFmpeg - not included but [easily installable on windows and linux](https://ffmpeg.org/download.html)
    - **If installing on ubuntu, ensure that ffmpeg version >= 4**
- gifski - windows executable is included. linux version [downloadable from the website](https://gif.ski/)
- pngquant - windows executable is included. installable on linux with `sudo apt-get install pngquant`
- ChromeDriver - ChromeDriver 87.0.4280.88 for both windows and linux are included. They have functioned as intended in
  my testing, but [here's the website anyways.](https://chromedriver.chromium.org/)
    - ChromeDriver requires there to be an installation of chrome on your system accessible via path or similair. Your
      chrome version doesn't have to be the exact same as your chromedriver version, but it should be similar
- ImageMagick - not included but [downloadable here](https://imagemagick.org/script/download.php)
- ExifTool - windows executable is included. installable on linux with `sudo apt-get install exiftool` https://exiftool.org/

### pip libraries

- This project uses [`pipenv`](https://github.com/pypa/pipenv), run `pipenv install` to install required dependencies.
- check [pipenv's repo](https://github.com/pypa/pipenv) for more info on pipenv usage.
- for now, a [`requirements.txt`](requirements.txt) file is also maintained, this may change.

### config

- create a copy of [`config.example.py`](config.example.py) and name it `config.py`.
- insert/change the appropriate config settings such as your discord api token. be sure not to add or remove quotes.
    - the 2 required config settings to change for proper functionality are the discord and tenor tokens.

### python

- developed and tested on python 3.8. use that or a later compatible version

### to run

- once you've set up all of the libraries, just run the program with `python main.py` (or `python3.8 main.py` or
  whatever your python is named). make sure it can read and write to the directory it lives in.
- terminate the bot by running the `shutdown` command, this will _probably_ close better than a termination
