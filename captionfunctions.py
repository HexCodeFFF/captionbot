import io
import random
import re
import subprocess
from PIL import Image, UnidentifiedImageError
import chromiumrender
from improcessing import filetostring, temp_file, mediatype

"""
This file contains all media processing functions that only work on one image/frame of video and must be run through 
improcessing.handleanimated()
"""


# stolen code https://stackoverflow.com/questions/6116978/how-to-replace-multiple-substrings-of-a-string
def replaceall(text, rep):
    """
    for instance of a key in rep, replace it with the value
    :param text: text to process
    :param rep: {valuetoreplace: toreplacewith, ...}
    :return: processed text
    """
    # use these three lines to do the replacement
    rep = dict((re.escape(k), v) for k, v in rep.items())
    # Python 3 renamed dict.iteritems to dict.items so use rep.items() for latest versions
    pattern = re.compile("|".join(rep.keys()))
    text = pattern.sub(lambda m: rep[re.escape(m.group(0))], text)
    return text


def sanitizehtml(text):
    """
    replace html characters with escaped characters to safely insert into html
    :param text: text to sanitize
    :return: sanitized text
    """
    if isinstance(text, list) or isinstance(text, tuple):
        text = list(text)
        text[:] = [c.replace("&", '&amp;').replace("<", '&lt;').replace(">", '&gt;').replace("\"", '&quot;')
                       .replace("'", '&#039;') for c in text]
    else:
        text = text.replace("&", '&amp;').replace("<", '&lt;').replace(">", '&gt;').replace("\"", '&quot;') \
            .replace("'", '&#039;')
    return text


def htmlcap(file, image, caption, tosavename=None):
    if tosavename is None:
        tosavename = temp_file("png")
    replacedict = {}
    if image:
        replacedict["rendering/demoimage.png"] = image
    if caption:
        caption = sanitizehtml(caption)
        if len(caption) == 1:
            replacedict["CaptionText"] = caption[0]
        else:
            for i, c in enumerate(caption):
                replacedict[f"CaptionText{i + 1}"] = c
    torender = replaceall(filetostring(file), replacedict)
    chromiumrender.html2png(torender, tosavename)
    return tosavename


# at some point i might remove these entirely and just have calls to htmlcap but i dont feel like changing all of
# this rn
def esmcaption(image, caption, tosavename=None):
    return htmlcap("captionhtml/esmcaption.html", image, caption, tosavename)


def caption(image, caption, tosavename=None):
    return htmlcap("captionhtml/mycaption.html", image, caption, tosavename)


def bottomcaption(image, caption, tosavename=None):
    return htmlcap("captionhtml/mycaptionbottom.html", image, caption, tosavename)


def stuff(image, caption, tosavename=None):
    return htmlcap("captionhtml/stuff.html", image, caption, tosavename)


def stuffstretch(image, caption, tosavename=None):
    return htmlcap("captionhtml/stuffstretch.html", image, caption, tosavename)


def motivate(image, caption, tosavename=None):
    return htmlcap("captionhtml/motivate.html", image, caption, tosavename)


def meme(image, caption, tosavename=None):
    return htmlcap("captionhtml/meme.html", image, caption, tosavename)


def tenorcap(image, caption, tosavename=None):
    return htmlcap("captionhtml/tenorcap.html", image, caption, tosavename)


def twittercap(image, caption, tosavename=None):
    return htmlcap("captionhtml/twittercaption.html", image, caption, tosavename)


def twittercapdark(image, caption, tosavename=None):
    return htmlcap("captionhtml/twittercaptiondark.html", image, caption, tosavename)


def eminemcap(image, caption, tosavename=None):
    return htmlcap("captionhtml/eminemcap.html", image, caption, tosavename)


def givemeyourphone(image, _, tosavename=None):
    return htmlcap("captionhtml/givemeyourphone.html", image, None, tosavename)


def eminem(caption, tosavename=None):
    return htmlcap("captionhtml/eminem.html", None, caption, tosavename)


def dontweet(caption, tosavename=None):
    return htmlcap("captionhtml/dontweet.html", None, caption, tosavename)


def resize(image, size, tosavename=None):
    """
    resizes image

    :param image: file
    :param width: new width, thrown directly into ffmpeg so it can be things like -1 or iw/2
    :param height: new height, same as width
    :param tosavename: optionally specify the file to save it to
    :return: processed media
    """
    width, height = size
    if tosavename is None:
        name = temp_file("png")
    else:
        name = tosavename
    subprocess.check_call(["ffmpeg", "-i", image, "-pix_fmt", "yuva420p",
                           "-sws_flags", "spline+accurate_rnd+full_chroma_int+full_chroma_inp",
                           "-vf", f"scale='{width}:{height}'", "-pix_fmt", "yuva420p", name],
                          stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    return name


def jpeg(image, params: list, tosavename=None):
    """
    makes image into badly compressed jpeg
    :param image: image
    :param params: [strength (# of iterations), stretch (random stretch), quality (jpeg quality)]
    :param tosavename: optionally specify file to save it to
    :return: processed media
    """
    if tosavename is None:
        name = temp_file("png")
    else:
        name = tosavename
    im = Image.open(image)
    im = im.convert("RGB")
    strength = params[0]
    stretch = params[1]
    quality = params[2]
    size = im.size
    for i in range(strength):
        im = im.resize((size[0] + random.randint(-stretch, stretch), size[1] + random.randint(-stretch, stretch)),
                       Image.NEAREST)
        stream = io.BytesIO()
        im.save(stream, format="JPEG", quality=quality)  # save image as jpeg to bytes
        stream.seek(0)
        im = Image.open(stream, formats=["JPEG"])
    im = im.resize(size)
    im.save(name)
    return name


def jpegcorrupt(image, randomchance, tosavename=None):
    """
    :param image: image
    :param randomchance: [% chance to randomly change jpeg byte]
    :param tosavename: optionally specify file to save it to
    :return:
    """
    randomchance = float(randomchance[0] / 100)
    # slight modification of https://github.com/HexCodeFFF/jpegcorruption
    if tosavename is None:
        tosavename = temp_file("png")
    im = Image.open(image)
    im = im.convert("RGB")
    stream = io.BytesIO()
    im.save(stream, format="jpeg")  # save image as jpeg to bytes
    stream.seek(0)
    imagebytes = stream.read()
    corrupting = True
    while corrupting:  # easy way to do a retry loop if corruption breaks the jpeg
        try:  # if image is invalid, PIL throws an error.
            cimagebytes = bytearray(imagebytes)  # easiest to deal with

            for i, byte in enumerate(imagebytes):
                if random.random() < randomchance:  # random.random() is 0-1
                    rb = random.randint(0, 255)  # get random byte
                    cimagebytes[i] = rb  # set corrupted byte
            # raise Exception(f"{len(cimagebytes)} {len(imagebytes)} {image}")
            imc = Image.open(io.BytesIO(cimagebytes))  # import corrupted jpeg to PIL image
            # an error will be thrown if image is invalid
            imc.save(tosavename)  # save frame
            corrupting = False  # this frame was successful, exit the while loop and go onto the next frame
        # errors that can be thrown if image is broken
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
            pass
    return tosavename


def magick(file, strength, tosavename=None):
    assert mediatype(file) == "IMAGE"
    if tosavename is None:
        tosavename = temp_file("png")
    subprocess.check_call(["magick", file, "-liquid-rescale", f"{strength[0]}%x{strength[0]}%", tosavename],
                          stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    return tosavename
