import asyncio
import glob
import logging
import os
import random
import string
import subprocess
import discord.ext
import typing
from PIL import Image
from winmagic import magic
from multiprocessing import Pool
import captionfunctions
import humanize

options = {
    "enable-local-file-access": None,
    "format": "png",
    "transparent": None,
    "width": 1,
    "quiet": None
}


def filetostring(f):
    with open(f, 'r') as file:
        data = file.read()
    return data


def get_random_string(length):
    return ''.join(random.choice(string.ascii_letters) for i in range(length))


def temp_file(extension="png"):
    while True:
        name = f"temp/{get_random_string(8)}.{extension}"
        if not os.path.exists(name):
            return name


# https://fredrikaverpil.github.io/2017/06/20/async-and-await-with-subprocesses/
async def run_command(*args):
    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    # Status
    logging.info(f"PID {process.pid} Started: {args}")

    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()

    # Progress
    if process.returncode == 0:
        logging.info(
            f"PID {process.pid} Done.",
        )
    else:
        logging.error(
            f"PID {process.pid} Failed: {args} result: {stderr.decode().strip()}",
        )
    result = stdout.decode().strip() + stderr.decode().strip()
    # Result

    # Return stdout
    return result


# https://askubuntu.com/questions/110264/how-to-find-frames-per-second-of-any-video-file
async def get_frame_rate(filename):
    logging.info("[improcessing] Getting FPS...")
    out = await run_command("ffprobe", filename, "-v", "0", "-select_streams", "v", "-print_format", "flat",
                            "-show_entries", "stream=r_frame_rate")
    rate = out.split('=')[1].strip()[1:-1].split('/')
    if len(rate) == 1:
        return float(rate[0])
    if len(rate) == 2:
        return float(rate[0]) / float(rate[1])
    return -1


# https://superuser.com/questions/650291/how-to-get-video-duration-in-seconds
async def get_duration(filename):
    logging.info("[improcessing] Getting FPS...")
    out = await run_command("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                            "default=noprint_wrappers=1:nokey=1", filename)
    return float(out)


async def ffmpegsplit(image):
    logging.info("[improcessing] Splitting frames...")
    await run_command("ffmpeg", "-i", image, "-vsync", "1", "-vf", "scale='max(200,iw)':-1",
                      f"{image.split('.')[0]}%09d.png")
    files = glob.glob(f"{image.split('.')[0]}*.png")

    return files, f"{image.split('.')[0]}%09d.png"


async def splitaudio(video):
    ifaudio = await run_command("ffprobe", "-i", video, "-show_streams", "-select_streams", "a", "-loglevel", "error")
    if ifaudio:
        logging.info("[improcessing] Splitting audio...")
        name = temp_file("aac")
        await run_command("ffmpeg", "-hide_banner", "-i", video, "-vn", "-acodec", "copy", name)
        return name
    else:
        logging.info("[improcessing] No audio detected.")
        return False


async def compresspng(png):
    outname = temp_file("png")
    await run_command("pngquant", "--quality=0-80", "--o", outname, png)
    os.remove(png)
    return outname


async def assurefilesize(image: str, ctx: discord.ext.commands.Context):
    for i in range(5):
        size = os.path.getsize(image)
        logging.info(f"Resulting file is {humanize.naturalsize(size)}")
        # https://www.reddit.com/r/discordapp/comments/aflp3p/the_truth_about_discord_file_upload_limits/
        if size >= 8388119:
            logging.info("Image too big!")
            msg = await ctx.send(f"⚠ Resulting file too big! ({humanize.naturalsize(size)}) Downsizing result...")
            await ctx.trigger_typing()
            image = await handleanimated(image, "", captionfunctions.halfsize)
            await msg.delete()
        if os.path.getsize(image) < 8388119:
            return image
    await ctx.send(f"⚠ Max downsizes reached. File is way too big.")
    return False


def minimagesize(image, minsize):
    im = Image.open(image)
    if im.size[0] < minsize:
        logging.info(f"[improcessing] Image is {im.size}, Upscaling image...")
        im = im.resize((minsize, round(im.size[1] * (minsize / im.size[0]))), Image.BICUBIC)
        name = temp_file("png")
        im.save(name)
        return name
    else:
        return image


def imagetype(image):
    mime = magic.from_file(image, mime=True)
    if "video" in mime:
        return "VIDEO"
    elif "image" in mime:
        with Image.open(image) as im:  # TODO: add a try catch just in case PIL doesn't support something
            anim = getattr(im, "is_animated", False)
        if anim:
            return "GIF"  # gifs dont have to be animated but if they aren't its easier to treat them like pngs
        else:
            return "IMAGE"
    return None


async def handleanimated(image: str, caption, capfunction: typing.Callable):
    imty = imagetype(image)
    logging.info(f"[improcessing] Detected type {imty}.")
    if imty is None:
        raise Exception(f"File {image} is invalid!")
    elif imty == "IMAGE":
        logging.info(f"[improcessing] Processing frame...")
        return await compresspng(capfunction(minimagesize(image, 200), caption))
    else:
        frames, name = await ffmpegsplit(image)
        audio = await splitaudio(image)
        fps = await get_frame_rate(image)
        logging.info(f"[improcessing] Processing {len(frames)} frames with {min(len(frames), 60)} processes...")
        capargs = []
        for i, frame in enumerate(frames):
            capargs.append((frame, caption, frame.replace('.png', '_rendered.png')))
        pool = Pool(min(len(frames), 60))  # cap processes
        pool.starmap_async(capfunction, capargs)
        pool.close()
        pool.join()
        logging.info(f"[improcessing] Joining {len(frames)} frames...")
        if imty == "GIF":
            outname = temp_file("gif")
            await run_command(
                "gifski", "--quiet", "-o", outname, "--fps", str(fps), "--width", "1000",
                name.replace('.png', '_rendered.png').replace('%09d', '*'))
        else:  # imty == "VIDEO":
            outname = temp_file("mp4")
            if audio:
                await run_command("ffmpeg", "-r", str(fps), "-start_number", "1", "-i",
                                  name.replace('.png', '_rendered.png'),
                                  "-i", audio, "-c:a", "aac", "-shortest",
                                  "-c:v", "libx264", "-crf", "25", "-pix_fmt", "yuv420p",
                                  "-vf", "crop=trunc(iw/2)*2:trunc(ih/2)*2", outname)
                os.remove(audio)
            else:
                await run_command("ffmpeg", "-r", str(fps), "-start_number", "1", "-i",
                                  name.replace('.png', '_rendered.png'),
                                  "-c:v", "libx264", "-crf", "25", "-pix_fmt", "yuv420p",
                                  "-vf", "crop=trunc(iw/2)*2:trunc(ih/2)*2", outname)
        # cleanup
        logging.info("[improcessing] Cleaning files...")
        for f in glob.glob(name.replace('%09d', '*')):
            os.remove(f)

        return outname


async def mp4togif(mp4):
    mime = magic.Magic(mime=True)
    filename = mime.from_file(mp4)
    if filename.find('video') == -1:
        return False
    frames, name = await ffmpegsplit(mp4)
    fps = await get_frame_rate(mp4)
    outname = temp_file("gif")
    await run_command("gifski", "--quiet", "-o", outname, "--fps", str(fps), name.replace('%09d', '*'))
    logging.info("[improcessing] Cleaning files...")
    for f in glob.glob(name.replace('%09d', '*')):
        os.remove(f)
    return outname


async def giftomp4(gif):
    outname = temp_file("mp4")
    await run_command("ffmpeg", "-i", gif, "-movflags", "faststart", "-pix_fmt", "yuv420p", "-vf",
                      "scale=trunc(iw/2)*2:trunc(ih/2)*2", outname)

    return outname


async def mediatopng(media):
    outname = temp_file("png")
    await run_command("ffmpeg", "-i", media, "-frames:v", "1", outname)

    return outname


async def ffprobe(file):
    return [await run_command("ffprobe", "-hide_banner", file), magic.from_file(file, mime=False),
            magic.from_file(file, mime=True)]


# https://stackoverflow.com/questions/65728616/how-to-get-ffmpeg-to-consistently-apply-speed-effect-to-first-few-frames
# TODO: some way to preserve gif transparency?
async def speed(file, sp):
    outname = temp_file("mp4")
    fps = await get_frame_rate(file)
    duration = await get_duration(file)
    ifaudio = await run_command("ffprobe", "-i", file, "-show_streams", "-select_streams", "a", "-loglevel", "error")
    if ifaudio:
        await run_command("ffmpeg", "-i", file, "-filter_complex",
                          f"[0:v]setpts=PTS/{sp},fps={fps}[v];[0:a]atempo={sp}[a]",
                          "-map", "[v]", "-map", "[a]", "-t", str(duration / float(sp)), outname)
    else:
        await run_command("ffmpeg", "-i", file, "-filter_complex",
                          f"[0:v]setpts=PTS/{sp},fps={fps}[v]",
                          "-map", "[v]", "-t", str(duration / float(sp)), outname)
    if imagetype(file) == "GIF":
        outname = await mp4togif(outname)
    return outname


async def quality(file, crf, qa):
    outname = temp_file("mp4")
    ifaudio = await run_command("ffprobe", "-i", file, "-show_streams", "-select_streams", "a", "-loglevel", "error")
    if ifaudio:
        await run_command("ffmpeg", "-i", file, "-crf", str(crf), "-c:a", "aac", "-q:a", str(qa), outname)
    else:
        await run_command("ffmpeg", "-i", file, "-crf", str(crf), outname)
    if imagetype(file) == "GIF":
        outname = await mp4togif(outname)
    return outname


async def changefps(file, fps):
    outname = temp_file("mp4")
    await run_command("ffmpeg", "-i", file, "-filter:v", f"fps=fps={fps}", outname)
    if imagetype(file) == "GIF":
        outname = await mp4togif(outname)
    return outname
