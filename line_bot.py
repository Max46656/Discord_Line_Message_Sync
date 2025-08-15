import datetime
import os
import urllib.parse
import requests
from discord import SyncWebhook, File
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage, \
    ReplyMessageRequest, TemplateMessage, ConfirmTemplate, MessageAction, PushMessageRequest, \
    ImageMessage, VideoMessage, AudioMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent, \
    VideoMessageContent, AudioMessageContent, StickerMessageContent, FileMessageContent, \
    LocationMessageContent
from pydantic import StrictStr
import logging

import line_sticker_downloader
import utilities as utils
from cache import sync_channels_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

config = utils.read_config()
configuration = Configuration(access_token=config['line_channel_access_token'])
handler = WebhookHandler(config['line_channel_secret'])
logger.info("Line Bot is ready.")

def get_bot_name() -> str:
    """Get the bot name.

    :return str: The bot name.
    """
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        profile = line_bot_api.get_bot_info()
        logger.debug(f"取得 LINE bot 名稱: {profile.display_name}")
        return profile.display_name

bot_name = get_bot_name()
dc_bot_invite_link = config['discord_bot_invite_link']

async def send_author_avatar(line_group_id: str, image_path: str):
    """使用 Messaging API 傳送使用者頭像到 LINE 群組。

    :param str line_group_id: LINE 群組 ID。
    :param str image_path: Discord雲端圖片檔案網址。
    """
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        try:
            #image_url = get_image_url(image_path)
            line_bot_api.push_message(PushMessageRequest(
                to=line_group_id,
                messages=[ImageMessage(originalContentUrl=image_path, previewImageUrl=image_path)]
            ))
            logger.info(f"成功傳送發言者頭像至 LINE 群組 {line_group_id}, URL: {image_path}")
        except Exception as e:
            logger.error(f"傳送發言者頭像至 LINE 群組 {line_group_id} 失敗: {e}")
            raise

def send_text_message(line_group_id: str, message: str):
    """Send text message to LINE group using Messaging API.

    :param str line_group_id: LINE group ID.
    :param str message: Message to send.
    """
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        try:
            line_bot_api.push_message(PushMessageRequest(
                to=line_group_id,
                messages=[TextMessage(text=message)]
            ))
            logger.info(f"成功傳送文字訊息至 LINE 群組 {line_group_id}: {message}")
        except Exception as e:
            logger.error(f"傳送文字訊息至 LINE 群組 {line_group_id} 失敗: {e}")
            raise

def send_image_message(line_group_id: str, message: str, image_path: str):
    """使用 Messaging API 傳送圖片訊息到 LINE 群組。

    :param str line_group_id: LINE 群組 ID。
    :param str message: 要傳送的文字訊息。
    :param str image_path: Discord雲端圖片檔案網址。
    """
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        try:
            #image_url = get_image_url(image_path)
            line_bot_api.push_message(PushMessageRequest(
                to=line_group_id,
                messages=[
                    TextMessage(text=message),
                    ImageMessage(originalContentUrl=image_path, previewImageUrl=image_path)
                ]
            ))
            logger.info(f"成功傳送圖片訊息至 LINE 群組 {line_group_id}: {message}, URL: {image_path}")
        except Exception as e:
            logger.error(f"傳送圖片訊息至 LINE 群組 {line_group_id} 失敗: {e}")
            raise

def send_video_message(line_group_id: str, message: str, video_path: str, thumbnail_path: str):
    """Send video message to LINE group using Messaging API.

    :param str line_group_id: LINE group ID.
    :param str message: Message to send.
    :param str video_path: Path to video file.
    :param str thumbnail_path: Path to thumbnail image.
    """
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        try:
            #video_url = upload_file(video_path)
            #thumbnail_url = upload_file(thumbnail_path)
            line_bot_api.push_message(PushMessageRequest(
                to=line_group_id,
                messages=[
                    TextMessage(text=message),
                    VideoMessage(originalContentUrl=video_path, previewImageUrl=thumbnail_path)
                ]
            ))
            logger.info(f"成功傳送影片訊息至 LINE 群組 {line_group_id}: {message}, Video URL: {video_path}")
        except Exception as e:
            logger.error(f"傳送影片訊息至 LINE 群組 {line_group_id} 失敗: {e}")
            raise

def send_audio_message(line_group_id: str, message: str, audio_path: str, audio_duration: int):
    """Send audio message to LINE group using Messaging API.

    :param str line_group_id: LINE group ID.
    :param str message: Message to send.
    :param str audio_path: Path to audio file.
    :param int audio_duration: Duration of audio in milliseconds.
    """
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        try:
            line_bot_api.push_message(PushMessageRequest(
                to=line_group_id,
                messages=[
                    TextMessage(text=message),
                    AudioMessage(originalContentUrl=audio_path, duration = 60)
                ]
            ))
            logger.info(f"成功傳送音訊訊息至 LINE 群組 {line_group_id}: {message}, Audio URL: {audio_path}")
        except Exception as e:
            logger.error(f"傳送音訊訊息至 LINE 群組 {line_group_id} 失敗: {e}")
            raise

def push_message(line_group_id: str, message: str):
    """Push a message to the specified LINE group.

    :param str line_group_id: LINE group ID.
    :param str message: Message to push.
    """
    send_text_message(line_group_id, message)

@app.post("/callback")
async def callback(request: Request):
    """Callback function for line webhook."""
    signature = request.headers['X-Line-Signature']
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
        logger.debug("成功處理 LINE webhook 回調")
    except InvalidSignatureError:
        logger.error("無效簽章。請檢查您的 LINE 頻道存取權杖或秘密金鑰。")
        raise HTTPException(status_code=400, detail="Invalid signature.")
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        if event.source.type == 'user':
            logger.debug("忽略來自單獨用戶的訊息")
            return
        line_bot_api = MessagingApi(api_client)
        message_received = event.message.text
        group_id = event.source.group_id
        logger.debug(f"收到 LINE 訊息: {message_received}, 群組: {group_id}")

        if group_id in sync_channels_cache.line_group_ids:
            author = line_bot_api.get_group_member_profile(group_id, event.source.user_id)
            dc_channel_webhook = sync_channels_cache.get_dc_webhook_by_line_group_id(group_id)
            discord_webhook = SyncWebhook.from_url(dc_channel_webhook)
            discord_webhook.send(message_received, username=f"{author.display_name} - (Line訊息)",
                                avatar_url=author.picture_url)
            logger.info(f"已傳送 LINE 訊息至 Discord: {message_received}")

        if message_received == "!ID":
            reply_message = TextMessage(text=f"Group ID: {group_id}")
        elif message_received == f"@{bot_name} ":
            if group_id in sync_channels_cache.line_group_ids:
                reply_message = TextMessage(text="此群組已綁定，新增綁定Discord頻道")
            #else:
            confirm_template = ConfirmTemplate(
                text=StrictStr("請問你的 Discord 伺服器邀請備份機器人了嗎？"),
                actions=[
                    MessageAction(label=StrictStr("還沒"),
                                    text=StrictStr("獲取 Discord 備份機器人邀請連結")),
                    MessageAction(label=StrictStr("已邀請"),
                                    text=StrictStr("確認並開始綁定"))
                ])
            reply_message = TemplateMessage(altText="是否完成加入 Discord 機器人？",
                                            template=confirm_template)
        elif message_received == "獲取 Discord 備份機器人邀請連結":
            if dc_bot_invite_link:
                reply_message = TextMessage(text=dc_bot_invite_link)
            else:
                reply_message = TextMessage(text="架設者未公開 Discord Bot 邀請連結")
        elif message_received == "確認並開始綁定":
            group_name = line_bot_api.get_group_summary(group_id).group_name
            binding_code = utils.generate_binding_code(group_id, group_name)
            reply_message = TextMessage(text=f"請至欲同步的Discord頻道中\n" \
                                            f"\n----------------------\n" \
                                            f"輸入以下指令來完成綁定\n" \
                                            f"/link {binding_code}\n" \
                                            f"----------------------\n" \
                                            f"\n※注意※\n" \
                                            f"此綁定碼僅能使用一次\n" \
                                            f"並將於5分鐘後過期")
        else:
            return
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token, messages=[reply_message]))
        logger.debug(f"回覆 LINE 訊息: {reply_message.text}")

@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker_message(event):
    with ApiClient(configuration) as api_client:
        if event.source.type == 'user':
            logger.debug("忽略來自單獨用戶的貼圖訊息")
            return
        line_bot_api = MessagingApi(api_client)
        group_id = event.source.group_id
        if group_id in sync_channels_cache.line_group_ids:
            subscribed_info = sync_channels_cache.get_info_by_line_group_id(group_id)
            author = line_bot_api.get_group_member_profile(group_id, event.source.user_id)
            is_animated = True if event.message.sticker_resource_type == 'ANIMATION' else False
            sticker_file = get_sticker_file(event.message.package_id, event.message.sticker_id, is_animated)
            if not sticker_file:
                logger.warning(f"無法找到貼圖: package_id={event.message.package_id}, sticker_id={event.message.sticker_id}")
                return
            discord_webhook = SyncWebhook.from_url(subscribed_info['discord_channel_webhook'])
            try:
                discord_webhook.send(file=File(sticker_file),
                                    username=f"{author.display_name} - (Line訊息)",
                                    avatar_url=author.picture_url)
                logger.info(f"已傳送貼圖至 Discord: {sticker_file}")
            finally:
                if os.path.exists(sticker_file):
                    os.remove(sticker_file)
                    logger.debug(f"已刪除貼圖檔案: {sticker_file}")

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    with ApiClient(configuration) as api_client:
        if event.source.type == 'user':
            logger.debug("忽略來自單獨用戶的圖片訊息")
            return
        line_bot_api = MessagingApi(api_client)
        group_id = event.source.group_id
        if group_id in sync_channels_cache.line_group_ids:
            subscribed_info = sync_channels_cache.get_info_by_line_group_id(group_id)
            author = line_bot_api.get_group_member_profile(group_id, event.source.user_id)
            file_path = download_content(event.message.id, subscribed_info['folder_name'], 'image')
            discord_webhook = SyncWebhook.from_url(subscribed_info['discord_channel_webhook'])
            try:
                discord_webhook.send(file=File(file_path),
                                    username=f"{author.display_name} - (Line訊息)",
                                    avatar_url=author.picture_url)
                logger.info(f"已傳送圖片至 Discord: {file_path}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"已刪除圖片檔案: {file_path}")

@handler.add(MessageEvent, message=VideoMessageContent)
def handle_video_message(event):
    with ApiClient(configuration) as api_client:
        if event.source.type == 'user':
            logger.debug("忽略來自單獨用戶的影片訊息")
            return
        line_bot_api = MessagingApi(api_client)
        group_id = event.source.group_id
        if group_id in sync_channels_cache.line_group_ids:
            subscribed_info = sync_channels_cache.get_info_by_line_group_id(group_id)
            author = line_bot_api.get_group_member_profile(group_id, event.source.user_id)
            file_path = download_content(event.message.id, subscribed_info['folder_name'], 'video')
            discord_webhook = SyncWebhook.from_url(subscribed_info['discord_channel_webhook'])
            try:
                discord_webhook.send(file=File(file_path),
                                    username=f"{author.display_name} - (Line訊息)",
                                    avatar_url=author.picture_url)
                logger.info(f"已傳送影片至 Discord: {file_path}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"已刪除影片檔案: {file_path}")

@handler.add(MessageEvent, message=AudioMessageContent)
def handle_audio_message(event):
    with ApiClient(configuration) as api_client:
        if event.source.type == 'user':
            logger.debug("忽略來自單獨用戶的音訊訊息")
            return
        line_bot_api = MessagingApi(api_client)
        group_id = event.source.group_id
        if group_id in sync_channels_cache.line_group_ids:
            subscribed_info = sync_channels_cache.get_info_by_line_group_id(group_id)
            author = line_bot_api.get_group_member_profile(group_id, event.source.user_id)
            file_path = download_content(event.message.id, subscribed_info['folder_name'], 'audio')
            discord_webhook = SyncWebhook.from_url(subscribed_info['discord_channel_webhook'])
            try:
                discord_webhook.send(file=File(file_path),
                                    username=f"{author.display_name} - (Line訊息)",
                                    avatar_url=author.picture_url)
                logger.info(f"已傳送音訊至 Discord: {file_path}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"已刪除音訊檔案: {file_path}")

@handler.add(MessageEvent, message=FileMessageContent)
def handle_file_message(event):
    with ApiClient(configuration) as api_client:
        if event.source.type == 'user':
            logger.debug("忽略來自單獨用戶的檔案訊息")
            return
        line_bot_api = MessagingApi(api_client)
        group_id = event.source.group_id
        if group_id in sync_channels_cache.line_group_ids:
            subscribed_info = sync_channels_cache.get_info_by_line_group_id(group_id)
            author = line_bot_api.get_group_member_profile(group_id, event.source.user_id)
            file_path = download_content(event.message.id, subscribed_info['folder_name'], 'file', file_name=event.message.file_name)
            discord_webhook = SyncWebhook.from_url(subscribed_info['discord_channel_webhook'])
            try:
                discord_webhook.send(file=File(file_path),
                                    username=f"{author.display_name} - (Line訊息)",
                                    avatar_url=author.picture_url)
                logger.info(f"已傳送檔案至 Discord: {file_path}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"已刪除檔案: {file_path}")

@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    with ApiClient(configuration) as api_client:
        if event.source.type == 'user':
            logger.debug("忽略來自單獨用戶的位置訊息")
            return
        line_bot_api = MessagingApi(api_client)
        group_id = event.source.group_id
        if group_id in sync_channels_cache.line_group_ids:
            subscribed_info = sync_channels_cache.get_info_by_line_group_id(group_id)
            author = line_bot_api.get_group_member_profile(group_id, event.source.user_id)
            location = event.message
            if hasattr(location, 'address') and location.address:
                encoded_address = urllib.parse.quote(location.address)
                google_maps_link = f"https://www.google.com/maps/place/{encoded_address}"
            else:
                google_maps_link = f"https://www.google.com/maps?q={location.latitude},{location.longitude}"

            location_message = f"📍 {author.display_name}分享了位置訊息\n\n"
            if hasattr(location, 'title') and location.title:
                location_message += f"地點名稱: **{location.title}**\n"
            if hasattr(location, 'address') and location.address:
                location_message += f"詳細地址: [{location.address}]({google_maps_link})\n"
            else:
                location_message += google_maps_link

            discord_webhook = SyncWebhook.from_url(subscribed_info['discord_channel_webhook'])
            discord_webhook.send(location_message, username=f"{author.display_name} - (Line訊息)",
                                avatar_url=author.picture_url)
            logger.info(f"已傳送位置訊息至 Discord: {location_message}")

def download_content(message_id: str, folder_name: str, content_type: str,
                     file_name: str = None) -> str:
    """Download content from LINE.

    :param str message_id: Message ID from LINE.
    :param str folder_name: The name of the folder you want to save files at.
    :param str content_type: File type, image, video, audio or file.
    :param str file_name: The file name you want to save as. Only used when content_type is file.
    :return str: The path of the downloaded file.
    """
    type_map = {
        'image': 'jpg',
        'video': 'mp4',
        'audio': 'm4a',
        'file': 'Get file name from args'
    }

    headers = {"Authorization": f"Bearer {config['line_channel_access_token']}"}
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        download_path = f"./downloads/{folder_name}/"
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        if content_type == 'file' and file_name is not None:
            file_name = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}_{file_name}"
        else:
            file_name = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}.{type_map[content_type]}"

        file_path = f"{download_path}{file_name}"
        with open(file_path, 'wb') as fd:
            for chunk in response.iter_content():
                fd.write(chunk)
        logger.debug(f"檔案下載成功: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"下載 LINE 內容失敗: message_id={message_id}, 錯誤: {e}")
        raise

def get_sticker_file(sticker_package_id: int, single_sticker_id: int,
                     is_animation: bool) -> str | None:
    """Get the sticker file path.

    :param int sticker_package_id: Sticker package ID.
    :param int single_sticker_id: Sticker ID.
    :param bool is_animation: Whether the sticker is animation.
    :return str: The path of the sticker file. None if failed.
    """
    base_dir = "./downloads/stickers"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)

    package_exists = False
    sticker_package_dir = None
    for folder_name in os.listdir(base_dir):
        if os.path.isdir(os.path.join(base_dir, folder_name)) and folder_name.startswith(
                f"{sticker_package_id}_"):
            package_exists = True
            sticker_package_dir = os.path.join(base_dir, folder_name)
            break
    if not package_exists:
        sticker_package_dir = line_sticker_downloader.download(sticker_package_id)

    for file_name in os.listdir(sticker_package_dir):
        if is_animation:
            if file_name.startswith(f"{single_sticker_id}.gif"):
                sticker_path = os.path.join(sticker_package_dir, file_name)
                logger.debug(f"找到動畫貼圖: {sticker_path}")
                return sticker_path
            continue
        else:
            if file_name.startswith(f"{single_sticker_id}.png"):
                sticker_path = os.path.join(sticker_package_dir, file_name)
                logger.debug(f"找到靜態貼圖: {sticker_path}")
                return sticker_path
            continue
    logger.warning(f"貼圖未找到: package_id={sticker_package_id}, sticker_id={single_sticker_id}")
    return None

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=config['webhook_port'])