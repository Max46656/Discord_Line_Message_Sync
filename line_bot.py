import uvicorn
from discord import SyncWebhook
from fastapi import FastAPI
from fastapi import Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage, \
    ReplyMessageRequest, TemplateMessage, ConfirmTemplate, MessageAction, PushMessageRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from pydantic import StrictStr

import utilities as utils
from cache import sync_channels_cache

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

config = utils.read_config()
webhook_url = config['webhook_url']


@app.post("/callback")
async def callback(request: Request):
    """Callback function for line webhook."""

    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = await request.body()

    # handle webhook body
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        raise HTTPException(status_code=400, detail="Invalid signature.")

    return 'OK'


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        if event.source.type == 'user':  # Exclude user messages, only process group messages
            return
        line_bot_api = MessagingApi(api_client)
        message_received = event.message.text
        group_id = event.source.group_id

        # Sync message to Discord
        if group_id in sync_channels_cache.line_group_ids:
            dc_channel_webhook = sync_channels_cache.get_dc_webhook_by_line_group_id(group_id)
            author = line_bot_api.get_group_member_profile(group_id, event.source.user_id)
            discord_webhook = SyncWebhook.from_url(dc_channel_webhook)
            discord_webhook.send(message_received, username=f"{author.display_name} - (Line訊息)",
                                 avatar_url=author.picture_url)

        # Handle commands messages
        if message_received == "!ID":
            reply_message = TextMessage(text=f"Group ID: {group_id}")
        elif message_received == "@訊息備份服務(DC) ":
            if group_id in sync_channels_cache.line_group_ids:
                reply_message = TextMessage(text="此群組已綁定")
            else:
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
            reply_message = TextMessage(text="邀請連結")
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


def push_message(line_group_id: str, message: str):
    """Push a message to the specified LINE group.

    :param str line_group_id: LINE group ID.
    :param str message: Message to push.
    """
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(PushMessageRequest(
            to=line_group_id, messages=[TextMessage(text=message)]))


if __name__ == '__main__':
    uvicorn.run(app, port=config['webhook_port'])
