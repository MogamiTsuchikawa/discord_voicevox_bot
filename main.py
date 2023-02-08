import discord
import requests
import json
import uuid
import time
import os
from dataclasses import dataclass
import re
from dotenv import load_dotenv
#load_dotenv()

VV_HOST = os.getenv("VV_HOST")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

speaker_list = [3, 2, 8, 10, 9, 11, 12, 13, 14, 16, 20, 21, 23, 27, 29, 42, 43, 46, 47]
speakername_list = ["ずんだもん","四国めたん","春日部つむぎ","雨晴はう","波音リツ","玄野武宏","白上虎太郎","青山龍星","冥鳴ひまり","九州そら", "もち子さん","剣崎雌雄","WhiteCUL", "後鬼","No.7","ちび式じい","櫻歌ミコ","小夜/SAYO","ナースロボ＿タイプＴ"]

@dataclass #これまだ使っていない、後でこれを使うように良い感じにする
class Speaker:
    id: int
    name: str


@dataclass
class ConectedUser:
    user_id: int
    voicevox_id: int


class ConnectedChannel:
    text_channel_id: int
    users: list[ConectedUser]
    select_speaker_index: int
    def __init__(self, text_channel_id):
        self.text_channel_id = text_channel_id
        self.users = []
        self.select_speaker_index = 0
    def say(self, content: str, user_id: int, message: discord.Message):
        if len(list(filter(lambda user : user.user_id == user_id, self.users))) == 0:
            self.users.append(ConectedUser(user_id, speaker_list[self.select_speaker_index]))
            self.select_speaker_index += 1
            if len(speaker_list) == self.select_speaker_index:
                self.select_speaker_index = 0
        target = list(filter(lambda user : user.user_id == user_id, self.users))[0]
        filename = str(uuid.uuid4())+".wav"
        generate_wav(content ,speaker=target.voicevox_id, filename=filename)
        while message.guild.voice_client.is_playing():
            pass
        message.guild.voice_client.play(discord.FFmpegPCMAudio("./audio/"+filename), after=lambda ex: os.remove(f"./audio/{filename}"))


connected_channels: list[ConnectedChannel] = []

host = VV_HOST
port = 50021
def generate_wav(text, speaker=1, filename='audio.wav'):
    params = (
        ('text', text),
        ('speaker', speaker),
    )
    response1 = requests.post(
        f'http://{host}:{port}/audio_query',
        params=params
    )
    headers = {'Content-Type': 'application/json',}
    response2 = requests.post(
        f'http://{host}:{port}/synthesis',
        headers=headers,
        params=params,
        data=json.dumps(response1.json())
    )
    with open("./audio/"+filename, 'wb') as f:
        f.write(response2.content)

def get_speaker_info(spaker_id: int) -> str:
    index = speaker_list.index(spaker_id)
    return speakername_list[index]

def find_url(content: str):
    return re.findall('https?://[A-Za-z0-9_/:%#$&?()~.=+-]+?(?=https?:|[^A-Za-z0-9_/:%#$&?()~.=+-]|$)', content)
def find_stamp(content: str):
    return re.findall('<:.*:[0-9]*>', content)
def find_mention(content: str):
    return re.findall('<@[0-9]*>', content)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message: discord.Message):
    # メッセージの送信者がbotだった場合は無視する
    if message.author.bot:
        return

    if message.content == "!join":
        if message.author.voice is None:
            await message.channel.send("あなたはボイスチャンネルに接続していません。")
            return
        # ボイスチャンネルに接続する
        await message.author.voice.channel.connect()
        #message.guild.voice_client.play(discord.FFmpegPCMAudio("example.mp3"))
        await message.channel.send("接続しました。")
        connected_channels.append(ConnectedChannel(message.channel.id))
        print(connected_channels)

    elif message.content == "!leave":
        if message.guild.voice_client is None:
            await message.channel.send("接続していません。")
            return

        # 切断する
        await message.guild.voice_client.disconnect()
        connected_channels.remove(list(filter(lambda channel : channel.text_channel_id == message.channel.id ,connected_channels))[0])
        print(connected_channels)

        await message.channel.send("切断しました。")
    elif message.content == "!sayhello":
        if message.guild.voice_client is None:
            await message.channel.send("接続していません。")
            return
    elif message.content == "!speakerinfo":
        channels = list(filter(lambda channel : channel.text_channel_id == message.channel.id ,connected_channels))
        if len(channels) > 0:
            users = list(filter(lambda user : user.user_id == message.author.id ,channels[0].users))
            if len(users) > 0:
                speaker_name = get_speaker_info(users[0].voicevox_id)
                await message.channel.send(message.author.display_name + ":" + speaker_name)
    elif message.content.find("!setspeaker") != -1:
        channels = list(filter(lambda channel : channel.text_channel_id == message.channel.id ,connected_channels))
        if len(channels) > 0:
            users = list(filter(lambda user : user.user_id == message.author.id ,channels[0].users))
            if len(users) > 0:
                try:
                    name = message.content.split(">")[1]
                    index = speakername_list.index(name)
                    users[0].voicevox_id = speaker_list[index]
                    await message.channel.send(f"{message.author.display_name}さんの声を「{name}」にしました")
                except:
                    await message.channel.send("正しくない形式です")
            else:
                await message.channel.send("喋るユーザーに登録されていません。何か書き込んでから再度試して下さい")
    elif message.content == "!listspeaker":
        rtnstr = ""
        for name in speakername_list:
            rtnstr += name + "\n"
        await message.channel.send(rtnstr)
    elif message.content == "!listdict":
        res = requests.get(f'http://{host}:{port}/user_dict')
        rtnstr = ""
        jsonres = res.json()
        rtnstr += f"ID:表記:発音（カタカナ）:音が下がる場所\n"
        for key in jsonres:
            rtnstr += f"{key}:{jsonres[key]['surface']}:{jsonres[key]['pronunciation']}:{jsonres[key]['accent_type']}\n"
        await message.channel.send(rtnstr)
    elif message.content.find("!adddict") != -1:
        cmds = message.content.split(">")
        if len(cmds) != 4 or int(cmds[3]) > len(cmds[2]):
            await message.channel.send("引数が不正です")
            return
        params = (
            ('surface', cmds[1]),
            ('pronunciation', cmds[2]),
            ('accent_type', int(cmds[3]))
        )
        res = requests.post(f'http://{host}:{port}/user_dict_word', params=params)
        if res.ok:
            await message.channel.send(":white_check_mark:追加に成功しました")
        else:
            await message.channel.send(":dizzy_face:追加に失敗しました")
            print(res.text)
    elif message.content.find("!deldict") != -1:
        cmds = message.content.split(">")
        if len(cmds) != 2:
            await message.channel.send("引数が不正です")
            return
        res = requests.delete(f'http://{host}:{port}/user_dict_word/{cmds[1]}')
        if res.ok:
            await message.channel.send(":wastebasket:削除に成功しました")
        else:
            await message.channel.send(":dizzy_face:削除に失敗しました")
            print(res.text)
    else:
        channels = list(filter(lambda channel : channel.text_channel_id == message.channel.id ,connected_channels))
        if len(channels) > 0:
            urls = find_url(message.content)
            stamps = find_stamp(message.content)
            mentions = find_mention(message.content)
            content = message.content
            print(content)
            print(urls)
            for url in urls:
                content = content.replace(url,"")
            for stamp in stamps:
                content = content.replace(stamp,"")
            for mention in mentions:
                content = content.replace(mention,"")
            if len(content) == 0:
                return
            channels[0].say(content, message.author.id, message)



# Botのトークンを指定（デベロッパーサイトで確認可能）
client.run(os.getenv("DISCORD_BOT_TOKEN"))