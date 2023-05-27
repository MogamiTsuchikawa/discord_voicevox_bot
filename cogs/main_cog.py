from discord.ext import commands
from discord import app_commands
import discord
from dataclasses import dataclass
import uuid
import os
import requests
import json
import csv
from typing import Dict
import re

VV_HOST = os.getenv("VV_HOST")
host = VV_HOST
port = 50021


def find_url(content: str):
    return re.findall('https?://[A-Za-z0-9_/:%#$&?()~.=+-]+?(?=https?:|[^A-Za-z0-9_/:%#$&?()~.=+-]|$)', content)


def find_stamp(content: str):
    return re.findall('<:.*:[0-9]*>', content)


def find_mention(content: str):
    return re.findall('<@[0-9]*>', content)


def generate_wav(text, speaker=1, filename='audio.wav'):
    params = (
        ('text', text),
        ('speaker', speaker),
    )
    response1 = requests.post(
        f'http://{host}:{port}/audio_query',
        params=params
    )
    headers = {'Content-Type': 'application/json', }
    response2 = requests.post(
        f'http://{host}:{port}/synthesis',
        headers=headers,
        params=params,
        data=json.dumps(response1.json())
    )
    with open("./audio/" + filename, 'wb') as f:
        f.write(response2.content)


class Speaker:
    def __init__(self, id: int, name: str):
        self.id: int = id
        self.name: str = name


@dataclass
class ConectedUser:
    user_id: int
    voicevox_id: int


class ConnectedChannel:
    text_channel_id: int
    users: Dict[ConectedUser]
    select_speaker_index: int

    def __init__(self, text_channel_id):
        self.text_channel_id = text_channel_id
        self.users: Dict[int, ConectedUser] = dict()
        self.select_speaker_index = 0

    def say(self, content: str, user_id: int, message: discord.Message):
        if user_id not in self.users:
            self.users[user_id] = ConectedUser(
                user_id, self.speaker_list[self.select_speaker_index].id)

        target = self.users[user_id]
        filename = str(uuid.uuid4()) + ".wav"
        generate_wav(content, speaker=target.voicevox_id, filename=filename)
        while message.guild.voice_client.is_playing():
            pass
        message.guild.voice_client.play(discord.FFmpegPCMAudio(
            "./audio/" + filename), after=lambda ex: os.remove(f"./audio/{filename}"))


class MainCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.speaker_list: Dict[Speaker] = dict()
        self.connected_channels: Dict[int, ConnectedChannel] = dict()

    def get_speaker_list(self):
        self.speaker_list = dict()
        with open("../speaker.csv", "r") as f:
            reader = csv.reader(f)
            for row in reader:
                speaker_id = int(row[0])
                self.speaker_list[speaker_id] = Speaker(speaker_id, row[1])

    @commands.Cog.listener()
    async def on_ready(self):

        print("maincog on ready")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id not in self.connected_channels:
            return
        if message.guild.voice_client is None:
            return
        urls = find_url(message.content)
        stamps = find_stamp(message.content)
        mentions = find_mention(message.content)
        for url in urls:
            message.content = message.content.replace(url, "")
        for stamp in stamps:
            message.content = message.content.replace(stamp, "")
        for mention in mentions:
            message.content = message.content.replace(mention, "")
        if message.content == "":
            return

        channel = self.connected_channels[message.channel.id]
        channel.say(message.content, message.author.id, message)

    @app_commands.command(name="join", description="ボイスチャンネルに参加します")
    async def join(self, interaction: discord.Interaction):
        if interaction.author.voice is None:
            return await interaction.response.send_message("ボイスチャンネルに参加してください")
        await interaction.user.voice.channel.connect()
        await interaction.response.send_message("参加しました")
        self.connected_channels[interaction.channel_id] = (
            ConnectedChannel(interaction.channel_id))
        print(self.connected_channels)

    @app_commands.command(name="leave", description="ボイスチャンネルから退出します")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client is None:
            return await interaction.response.send_message("ボイスチャンネルに参加していません")
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("退出しました")
        del self.connected_channels[interaction.channel_id]

    @app_commands.command(name="speakerinfo", description="キャラクター情報を表示します")
    async def speakerinfo(self, interaction: discord.Interaction):
        if interaction.guild.voice_client is None:
            return await interaction.response.send_message("ボイスチャンネルに参加していません")

        channel = self.connected_channels[interaction.channel_id]
        if interaction.user.id not in channel.users:
            return await interaction.response.send_message("未登録です")

        user = channel.users[interaction.user.id]
        await interaction.response.send_message(f"{interaction.author.display_name}:{str(user.voicevox_id)}")

    @app_commands.command(name="setspeaker", description="キャラクターを変更します")
    @app_commands.describe(speaker_id="キャラクターIDを入力してください(/speakerlistで確認できます)")
    async def setspeaker(self, interaction: discord.Interaction, speaker_id: int):
        if interaction.guild.voice_client is None:
            return await interaction.response.send_message("ボイスチャンネルに参加していません")
        if interaction.user not in interaction.channel.users:
            return await interaction.response.send_message("喋るユーザーに登録されていません。何か書き込んでから再度試して下さい")
        if speaker_id in self.speaker_list:
            return await interaction.response.send_message("存在しないキャラクターです")
        channel = self.connected_channels[interaction.channel_id]
        user = channel.users[interaction.author.id]
        user.voicevox_id = speaker_id
        return await interaction.response.send_message(f"{interaction.author.display_name}:{str(user.voicevox_id)}")

    @app_commands.command(name="speakerlist", description="キャラクター一覧を表示します")
    async def speakerlist(self, interaction: discord.Interaction):
        message = "```"
        for speaker in self.speaker_list:
            message += f"{speaker.id}:{speaker.name}\n"
        message += "```"
        return await interaction.response.send_message(message)

    @app_commands.command(name="dict", description="辞書を表示します")
    async def dict(self, interaction: discord.Interaction):
        res = requests.get(f'http://{host}:{port}/user_dict')
        rtnstr = ""
        jsonres = res.json()
        rtnstr += "ID:表記:発音（カタカナ）:音が下がる場所\n"
        for key in jsonres:
            rtnstr += f"{key}:{jsonres[key]['surface']}:{jsonres[key]['pronunciation']}:{jsonres[key]['accent_type']}\n"
        await interaction.response.send_message(rtnstr)

    @app_commands.command(name="add", description="辞書に単語を追加します")
    @app_commands.describe(surface="表記", pronunciation="発音（カタカナ）", accent_type="音が下がる場所")
    async def add(self, interaction: discord.Interaction, surface: str, pronunciation: str, accent_type: int):
        params = {'surface': surface, 'pronunciation': pronunciation,
                  'accent_type': accent_type}
        res = requests.post(
            f'http://{host}:{port}/user_dict_word', params=params)
        if res.ok:
            await interaction.response.send_message(":white_check_mark:追加に成功しました")
        else:
            await interaction.response.send_message(":dizzy_face:追加に失敗しました")

    @app_commands.command(name="delete", description="辞書から単語を削除します")
    @app_commands.describe(word_id="単語のIDを入力してください(/dictで確認できます)")
    async def delete(self, interaction: discord.Interaction, word_id: int):
        res = requests.delete(
            f'http://{host}:{port}/user_dict_word/{word_id}')
        if res.ok:
            await interaction.response.send_message(":wastebasket:削除に成功しました")
        else:
            await interaction.response.send_message(":dizzy_face:削除に失敗しました")
