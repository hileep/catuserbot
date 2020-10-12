import asyncio
import json
import os
import subprocess
import time
from pathlib import Path

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from telethon.tl.types import DocumentAttributeVideo

from ..utils import admin_cmd, edit_or_reply, progress, sudo_cmd
from . import CMD_HELP, LOGS, parse_pre

thumb_image_path = Config.TMP_DOWNLOAD_DIRECTORY + "/thumb_image.jpg"


async def catlst_of_files(path):
    files = []
    for dirname, dirnames, filenames in os.walk(path):
        # print path to all filenames.
        for filename in filenames:
            files.append(os.path.join(dirname, filename))
    return files


def get_video_thumb(file, output=None, width=320):
    output = file + ".jpg"
    metadata = extractMetadata(createParser(file))
    p = subprocess.Popen(
        [
            "ffmpeg",
            "-i",
            file,
            "-ss",
            str(
                int((0, metadata.get("duration").seconds)[metadata.has("duration")] / 2)
            ),
            # '-filter:v', 'scale={}:-1'.format(width),
            "-vframes",
            "1",
            output,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    p.communicate()
    if not p.returncode and os.path.lexists(file):
        return output


def extract_w_h(file):
    """ Get width and height of media """
    command_to_run = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        file,
    ]
    # https://stackoverflow.com/a/11236144/4723940
    try:
        t_response = subprocess.check_output(command_to_run, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        LOGS.warning(exc)
    else:
        x_reponse = t_response.decode("UTF-8")
        response_json = json.loads(x_reponse)
        width = int(response_json["streams"][0]["width"])
        height = int(response_json["streams"][0]["height"])
        return width, height


async def upload(path, event, udir_event):
    global uploaded
    if os.path.isfile(path):
        caption_rts = os.path.basename(path)
        c_time = time.time()
        thumb = None
        if os.path.exists(thumb_image_path):
            thumb = thumb_image_path
        if not caption_rts.lower().endswith(".mp4"):
            await event.client.send_file(
                event.chat_id,
                path,
                caption=caption_rts,
                force_document=False,
                thumb=thumb,
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(d, t, udir_event, c_time, "Uploading...", path)
                ),
            )
        else:
            metadata = extractMetadata(createParser(path))
            duration = 0
            width = 0
            height = 0
            if metadata.has("duration"):
                duration = metadata.get("duration").seconds
            if metadata.has("width"):
                width = metadata.get("width")
            if metadata.has("height"):
                height = metadata.get("height")
            await event.client.send_file(
                event.chat_id,
                path,
                caption=caption_rts,
                thumb=thumb,
                force_document=False,
                supports_streaming=True,
                attributes=[
                    DocumentAttributeVideo(
                        duration=duration,
                        w=width,
                        h=height,
                        round_message=False,
                        supports_streaming=True,
                    )
                ],
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(d, t, udir_event, c_time, "Uploading...", path)
                ),
            )
        uploaded += 1
    elif os.path.isdir(path):
        await event.client.send_message(
            event.chat_id,
            path,
            parse_mode=parse_pre,
        )
        Files = os.listdir(path)
        Files.sort()
        for file in Files:
            path = os.path.join(path, file)
            await upload(path, event, udir_event)


@bot.on(admin_cmd(pattern="upload (.*)", outgoing=True))
@bot.on(sudo_cmd(pattern="upload (.*)", allow_sudo=True))
async def uploadir(event):
    global uploaded
    input_str = event.pattern_match.group(1)
    path = Path(input_str)
    if not os.path.exists(path):
        await edit_or_reply(
            event,
            f"there is no such directory/file with the name `{path}` to upload",
        )
        return
    udir_event = await edit_or_reply(event, "Uploading....")
    if os.path.isdir(path):
        udir_event = await edit_or_reply(
            event, f"Gathering file details in directory `{path}`"
        )
        await upload(path, event, udir_event)
        uploaded = 0
        await udir_event.edit("Uploaded `{}` files successfully !!".format(uploaded))
    else:
        udir_event = await edit_or_reply(event, f"`Uploading.....`")
        await upload(path, event, udir_event)
        await udir_event.delete()


@bot.on(admin_cmd(pattern="uploadas(stream|vn|all) (.*)", outgoing=True))
@bot.on(sudo_cmd(pattern="uploadas(stream|vn|all) (.*) ", allow_sudo=True))
async def uploadas(event):
    # For .uploadas command, allows you to specify some arguments for upload.
    type_of_upload = event.pattern_match.group(1)
    input_str = event.pattern_match.group(2)
    uas_event = await edit_or_reply(event, "uploading.....")
    supports_streaming = False
    round_message = False
    spam_big_messages = False
    if type_of_upload == "all":
        spam_big_messages = True
    elif type_of_upload == "stream":
        supports_streaming = True
    elif type_of_upload == "vn":
        round_message = True
    thumb = None
    file_name = None
    if "|" in input_str:
        file_name, thumb = input_str.split("|")
        file_name = file_name.strip()
        thumb = thumb.strip()
    else:
        file_name = input_str
        thumb = vthumb = get_video_thumb(file_name)
    if not thumb and os.path.exists(thumb_image_path):
        thumb = thumb_image_path
    if os.path.exists(file_name):
        metadata = extractMetadata(createParser(file_name))
        duration = 0
        width = 0
        height = 0
        if metadata.has("duration"):
            duration = metadata.get("duration").seconds
        if metadata.has("width"):
            width = metadata.get("width")
        if metadata.has("height"):
            height = metadata.get("height")
        try:
            if supports_streaming:
                c_time = time.time()
                await borg.send_file(
                    uas_event.chat_id,
                    file_name,
                    thumb=thumb,
                    caption=input_str,
                    force_document=False,
                    allow_cache=False,
                    reply_to=event.message.id,
                    attributes=[
                        DocumentAttributeVideo(
                            duration=duration,
                            w=width,
                            h=height,
                            round_message=False,
                            supports_streaming=True,
                        )
                    ],
                    progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                        progress(d, t, uas_event, c_time, "Uploading...", file_name)
                    ),
                )
            elif round_message:
                c_time = time.time()
                await borg.send_file(
                    uas_event.chat_id,
                    file_name,
                    thumb=thumb,
                    allow_cache=False,
                    reply_to=event.message.id,
                    video_note=True,
                    attributes=[
                        DocumentAttributeVideo(
                            duration=60,
                            w=1,
                            h=1,
                            round_message=True,
                            supports_streaming=True,
                        )
                    ],
                    progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                        progress(d, t, uas_event, c_time, "Uploading...", file_name)
                    ),
                )
            elif spam_big_messages:
                await uas_event.edit("TBD: Not (yet) Implemented")
                return
            try:
                os.remove(vthumb)
            except BaseException:
                pass
            await uas_event.edit("Uploaded successfully !!")
        except FileNotFoundError as err:
            await uas_event.edit(str(err))
    else:
        await uas_event.edit("404: File Not Found")


CMD_HELP.update(
    {
        "upload": "**Plugin :** `upload`\
    \n\n**Syntax :** `.upload path of file`\
    \n**Usage : **Uploads the file from the server\
    \n\n**Syntax : **`.uploadasstream path of video/audio`\
    \n**Usage : **Uploads video/audio as streamable from the server\
    \n\n**Syntax : **`.uploadasvn path of video`\
    \n**Usage : **Uploads video/audio as round video from the server **Present supports few videos need to work onit takes some time to develop it **\
    "
    }
)
