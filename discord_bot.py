import time
import re

import discord
from discord import app_commands
from discord.ext import commands
import logging

import line_bot
import utilities as utils
from cache import sync_channels_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

config = utils.read_config()

intents = discord.Intents.all() 
client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

supported_image_format = ('.jpg', '.png', '.jpeg', '.webp')
supported_video_format = ('.mp4','.webm','.ts')
supported_audio_format = ('.m4a', '.wav', '.mp3', '.aac', '.flac', '.ogg', '.opus')

async def on_ready():
    """Initialize discord bot."""
    logger.info("DC Bot is ready.")
    try:
        synced = await client.tree.sync()
        logger.info(f"Synced {synced} commands.")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@app_commands.describe()
async def about(interaction: discord.Interaction):
    subscribed_info = sync_channels_cache.get_info_by_dc_channel_id(interaction.channel.id)
    if subscribed_info:
        sync_info = f"=======================================\n" \
                    f"Discord頻道：{subscribed_info['discord_channel_name']}\n" \
                    f"Line群組      ：{subscribed_info['line_group_name']}\n" \
                    f"=======================================\n"
    else:
        sync_info = f"尚未與任何 LINE 群組連動備份！\n"
    all_commands = await client.tree.fetch_commands()
    help_command = discord.utils.get(all_commands, name="help")
    embed_message = discord.Embed(title="LINE ⇄ Discord 訊息備份機器人",
                                 description=f"一個協助你同步 Discord 與 LINE 訊息的免費服務\n\n"
                                             f"目前同步備份的服務：\n"
                                             f"{sync_info}\n"
                                             f"此專案由 [樂弟](https://github.com/HappyGroupHub) 開發，"
                                             f"此分支由 [麥克思](https://github.com/Max46656) 維護。"
                                             f"你可以使用指令 {help_command.mention} 了解如何\n使用此機器人\n",
                                 color=0x2ecc71)
    embed_message.set_author(name=client.user.name, icon_url=client.user.avatar)
    embed_message.add_field(name="作者", value="LD", inline=True)
    embed_message.add_field(name="架設者", value=config['bot_hosted_by'], inline=True)
    embed_message.add_field(name="版本", value="v0.5.3", inline=True)
    await interaction.response.send_message(embed=embed_message, view=AboutCommandView())

class AboutCommandView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=0)
        if config['line_bot_invite_link'] != '':
            self.add_item(discord.ui.Button(label="Line Bot邀請連結",
                                            url=config['line_bot_invite_link'],
                                            style=discord.ButtonStyle.link,
                                            emoji="💬", row = 1))
        if config['discord_bot_invite_link'] != '':
            self.add_item(discord.ui.Button(label="Discord Bot邀請連結",
                                            url=config['discord_bot_invite_link'],
                                            style=discord.ButtonStyle.link,
                                            emoji="🤖", row = 1))
        self.add_item(discord.ui.Button(label="Github原始碼",
                                        url="https://github.com/Max46656/Discord_Line_Message_Sync",
                                        style=discord.ButtonStyle.link,
                                        emoji="🔬", row = 0))
        self.add_item(discord.ui.Button(label="回報錯誤",
                                url="https://github.com/Max46656/Discord_Line_Message_Sync/issues",
                                style=discord.ButtonStyle.link,
                                emoji="🔬", row = 0))

@app_commands.describe()
async def help(interaction: discord.Interaction):
    all_commands = await client.tree.fetch_commands()
    about_command = discord.utils.get(all_commands, name="about")
    link_command = discord.utils.get(all_commands, name="link")
    unlink_command = discord.utils.get(all_commands, name="unlink")
    embed_message = discord.Embed(title="LINE ⇄ Discord 訊息備份機器人",
                                 description=f"`1.` {about_command.mention}｜關於機器人\n"
                                             f"> 查看機器人的詳細資訊, 以及目前連動備份中的服務\n\n"
                                             f"`2.` {link_command.mention}｜綁定Line群組並開始備份\n"
                                             f"> 邀請Line Bot至群組中並直接 tag(@) 該機器人\n"
                                             f"> 獲得Discord綁定碼後即可使用此指令連動備份\n\n"
                                             f"`3.` {unlink_command.mention}｜解除Line群組綁定並取消備份\n"
                                             f"> 解除與Line群組的綁定, 並取消連動備份服務\n\n",
                                 color=0x2ecc71)
    embed_message.set_author(name=client.user.name, icon_url=client.user.avatar)
    await interaction.response.send_message(embed=embed_message)

@app_commands.describe(binding_code="輸入你的綁定碼")
async def link(interaction: discord.Interaction, binding_code: int):
    logger.debug(f"收到 /link 指令，綁定碼: {binding_code}")
    binding_info = utils.get_binding_code_info(str(binding_code))
    if binding_info is None:
        reply_message = "綁定失敗, 該綁定碼輸入錯誤或格式不正確, 請再試一次."
        logger.warning(f"綁定失敗，無效綁定碼: {binding_code}")
        await interaction.response.send_message(reply_message, ephemeral=True)
    elif binding_info['expiration'] < time.time():
        utils.remove_binding_code(binding_code)
        reply_message = "綁定失敗, 此綁定碼已逾5分鐘內無使用而過期, 請再試一次."
        logger.warning(f"綁定失敗，綁定碼 {binding_code} 已過期")
        await interaction.response.send_message(reply_message, ephemeral=True)
    else:
        webhook = await interaction.channel.create_webhook(name="Line訊息同步")
        utils.add_new_sync_channel(binding_info['line_group_id'], binding_info['line_group_name'],
                                   interaction.channel.id, interaction.channel.name, webhook.url)
        utils.remove_binding_code(binding_code)
        push_message = f"綁定成功！\n" \
                       f"     ----------------------\n" \
                       f"    |    LINE ⇄ Discord   |\n" \
                       f"    |    雙向連動機器人   |\n" \
                       f"     ----------------------\n\n" \
                       f"Discord頻道：{interaction.channel.name}\n" \
                       f"Line群組      ：{binding_info['line_group_name']}\n" \
                       f"===================\n" \
                       f"目前支援連動備份：文字訊息、圖片、影片、音訊與其他附件"
        reply_message = f"**【LINE ⇄ Discord 雙向連動機器人 - 綁定成功！】**\n\n" \
                        f"Discord頻道：{interaction.channel.name}\n" \
                        f"Line群組      ：{binding_info['line_group_name']}\n" \
                        f"========================================\n" \
                        f"目前支援連動備份：文字訊息、圖片、影片、音訊與其他附件"
        logger.info(f"綁定成功: Discord 頻道 {interaction.channel.name} -> LINE 群組 {binding_info['line_group_name']}")
        line_bot.push_message(binding_info['line_group_id'], push_message)
        await interaction.response.send_message(reply_message)

@app_commands.describe()
async def unlink(interaction: discord.Interaction):
    subscribed_info = sync_channels_cache.get_info_by_dc_channel_id(interaction.channel.id)
    if not subscribed_info:
        reply_message = "此頻道並未綁定任何Line群組！"
        logger.warning(f"解除綁定失敗，頻道 {interaction.channel.id} 未綁定")
        await interaction.response.send_message(reply_message, ephemeral=True)
    else:
        reply_message = f"**【LINE ⇄ Discord - 解除連動備份！】**\n\n" \
                        f"Discord頻道：{subscribed_info['discord_channel_name']}\n" \
                        f"Line群組      ：{subscribed_info['line_group_name']}\n" \
                        f"========================================\n" \
                        f"請問確定要解除同步嗎？"
        await interaction.response.send_message(reply_message,
                                               view=UnlinkConfirmation(subscribed_info),
                                               ephemeral=True)

class UnlinkConfirmation(discord.ui.View):
    def __init__(self, subscribed_info):
        super().__init__(timeout=20)
        self.subscribed_info = subscribed_info

    @discord.ui.button(label="⛓️ 確認解除同步", style=discord.ButtonStyle.danger)
    async def unlink_confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        utils.remove_sync_channel(discord_channel_id=self.subscribed_info['discord_channel_id'])
        push_message = f"已解除同步！\n" \
                       f"     ----------------------\n" \
                       f"    |    LINE ⇄ Discord   |\n" \
                       f"    |    雙向連動機器人   |\n" \
                       f"     ----------------------\n\n" \
                       f"Discord頻道：{self.subscribed_info['discord_channel_name']}\n" \
                       f"Line群組      ：{self.subscribed_info['line_group_name']}\n" \
                       f"===================\n" \
                       f"執行者：{interaction.user.display_name}\n"
        reply_message = f"**【LINE ⇄ Discord 雙向連動機器人 - 已解除同步！】**\n\n" \
                        f"Discord頻道：{self.subscribed_info['discord_channel_name']}\n" \
                        f"Line群組      ：{self.subscribed_info['line_group_name']}\n" \
                        f"========================================\n" \
                        f"執行者：{interaction.user.display_name}\n"
        self.stop()
        logger.info(f"解除綁定成功: Discord 頻道 {self.subscribed_info['discord_channel_name']} -> LINE 群組 {self.subscribed_info['line_group_name']}")
        line_bot.push_message(self.subscribed_info['line_group_id'], push_message)
        await interaction.response.send_message(reply_message)

    @discord.ui.button(label="取消操作", style=discord.ButtonStyle.primary)
    async def unlink_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        reply_message = "操作已取消！"
        self.stop()
        logger.info("解除綁定操作已取消")
        await interaction.response.send_message(reply_message, ephemeral=True)

@client.event
async def on_message(message):
    """Handle message event."""
    logger.info(f"接收到訊息: {message.content}, 來自: {message.author.name}, 頻道: {message.channel.id} 提及:{message.mentions}{message.channel_mentions}{message.role_mentions}")
    if message.author.bot:
        logger.debug("訊息來自機器人自身或其他非人類使用者，已忽略回音")
        await client.process_commands(message)
        return
    if message.channel.type == discord.ChannelType.public_thread or message.channel.type == discord.ChannelType.news_thread:
        subscribed_info = sync_channels_cache.get_info_by_dc_channel_id(message.channel.parent_id)
    else:
        subscribed_info = sync_channels_cache.get_info_by_dc_channel_id(message.channel.id)

    if not subscribed_info:
        logger.warning(f"未找到頻道 {message.channel.id} 的訂閱資訊")
        await client.process_commands(message)
        return
    line_group_id = subscribed_info['line_group_id']
    author = message.author.display_name
    logger.debug(f"準備傳送訊息到 LINE 群組 {line_group_id}, 作者: {author}")
    try:
        #await line_bot.send_author_avatar(line_group_id,re.sub(r'\?.*$', '', message.author.avatar.url))
        if message.attachments:
            for attachment in message.attachments:
                logger.debug(f"處理附件: {attachment}")
                try:
                    if attachment.filename.lower().endswith(supported_image_format):
                        message_content = message.content or f"{author}\n在 {message.channel}\n傳送了圖片 {attachment.title}"
                        line_bot.send_image_message(line_group_id, message_content, attachment.url)
                    elif attachment.filename.lower().endswith(supported_video_format):
                        message_content = message.content or f"{author}\n在 {message.channel}\n傳送了影片 {attachment.title}"
                        thumbnail_path = attachment.proxy_url #取得縮圖過於麻煩，有檔名提示即可
                        line_bot.send_video_message(line_group_id, message_content, attachment.url, thumbnail_path)

                    elif attachment.filename.lower().endswith(supported_audio_format):
                        message_content = message.content or f"{author}\n在 {message.channel}\n傳送了音訊 {attachment.title}"
                        line_bot.send_audio_message(line_group_id, message_content, attachment.url, attachment.size/128)
                    else:
                        message_content = f"{message.name}\n在 {message.channel}\n 傳送了檔案 {attachment.title}\n (URL: {attachment.url})"
                        line_bot.send_image_message(line_group_id, message_content, message.author.avatar)
                        line_bot.send_text_message(line_group_id, message_content)
                except Exception as e:
                    logger.error(f"處理 Discord 附件時發生錯誤: {e}")
        else:
            message_content = message.content
            if message.mentions:
                for mention in message.mentions:
                    message_content = re.sub(rf'<@!?{mention.id}>',"@"+mention.display_name, message_content)
            if message.role_mentions:
                for role in message.role_mentions:
                    message_content = re.sub(rf'<@&{role.id}>', "@"+role.name, message_content)
            if message.channel_mentions:
                for channel in message.channel_mentions:
                    message_content = re.sub(rf'<#{channel.id}>', "#"+channel.name, message_content)
            message_content = (f"{author}\n在 {message.channel.name}：\n{message_content}") or f"{author}: [無文字內容]"
            logger.info(f"傳送文字訊息: {message_content}")
            line_bot.send_text_message(line_group_id, message_content)

    except Exception as e:
        logger.error(f"處理 Discord 訊息時發生錯誤: {e}")
    await client.process_commands(message)

if __name__ == '__main__':
    client.run(config.get('discord_bot_token'))