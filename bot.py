import discord
from discord.ext import commands,tasks
from discord.utils import get
from discord import FFmpegPCMAudio
import asyncio
import youtube_dl
import os
import math

from dotenv import load_dotenv

load_dotenv()

help_command = commands.DefaultHelpCommand(
  no_category = 'Commands'
)

os.system('cls')
bot = commands.Bot(command_prefix='-',help_command = help_command)

password = str(os.getenv("bot_key"))

playlist = []
queue = []
waiting = False
looping = False
loop_current = False
last_song = {}
try:
  async def play_song(ctx,song=None):
    global queue
    global loop_current
    global last_song
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    if song == None:
      await ctx.send(f"**Skipped**")
      if len(queue) >= 1:
        song = queue.pop(0)
      elif len(queue) == 0:
        last_song = {}
        if not looping:
          await ctx.send("**Queue is now empty**",delete_after=20)
        return
    elif song == "same_song":
      song = last_song
    source = await discord.FFmpegOpusAudio.from_probe(song['url'],**FFMPEG_OPTIONS)
    converted_duration = await convert_duration(song['duration'])
    if ctx.voice_client.is_playing() == True:
      queue.append(song)
      length = len(queue)
      await ctx.send(content=f"Added to **#{length}** in queue: {song['title']} ({converted_duration})")
    elif ctx.voice_client.is_playing() == False:
      last_song = song
      ctx.voice_client.play(source,after=lambda ex: ctx.bot.loop.create_task(check_queue(ctx)))
      await ctx.send(content=f"**Now Playing:** {song['title']} ({converted_duration})")

  async def check_queue(ctx):
    global loop_current
    if (len(queue) >=1):
      loop_current = False
      next_song = queue.pop(0)
      if looping:
        queue.append(last_song)
      await play_song(ctx,next_song)
    else:
      if looping:
        loop_current= True
        await play_song(ctx,"same_song")
      else:
        loop_current=False

  async def convert_duration(duration):
    minutes = str(math.floor(duration/60))
    seconds = str(duration%60)
    if len(seconds) == 1:
      seconds + "0"
    return f"{minutes}:{seconds}"

  @bot.event
  async def on_ready():
    print(f'{bot.user} logged in')

  @bot.command(help = 'Loops the queue playlist',aliases=['r','R','Repeat'])
  async def repeat(ctx):
    global looping
    global queue
    if not looping:
      looping = True
      if len(queue) == 1:
        await ctx.send(content=f"**Now Repeating:** 1 song")
      else:
        await ctx.send(content=f"**Now Repeating:** {len(queue)+1} songs")
    elif looping:
      looping = False
      await ctx.send(content="**No Longer Repeating**",delete_after=20)
      
  @bot.command(help= 'Displays the current queue,aswell as the currently playing song',aliases=['q','Q','Queue','queue'])
  async def displayqueue(ctx):
    i=0
    if last_song != {}:
      converted_duration = await convert_duration(last_song['duration'])
      message = await ctx.send(f'**Now Playing:** {last_song["title"]} ({converted_duration})')
    else:
      message = await ctx.send(f'**No song currently playing**')
    if queue != []:
      await message.edit(content=f'{message.content} \n**Current Queue:**')
      for song in queue:
        i += 1
        converted_duration = await convert_duration(song['duration'])
        await message.edit(content=f'{message.content}\n**{i}:** {song["title"]} ({converted_duration})')
    elif queue == []:
      await ctx.send('**Queue is empty!**')

  @bot.command(help='Skips the current song',aliases=['s','S','Skip'])
  async def skip(ctx):
    ctx.voice_client.stop()
    converted_duration = await convert_duration(last_song['duration'])
    await ctx.send(f"**Skipped:** {last_song['title']} ({converted_duration})")

  @bot.command(help = 'Shuts down the bot. Can only be used by Rybot')
  async def shutdown(ctx):
    messager = ctx.message.author
    if messager.id == 404491098946273280:
      await ctx.send(content=f"Ok {messager.name}, shutting down the bot",delete_after=20)
      exit()
    else:
      await ctx.send(content=f"Sorry {messager.name},only Rybot can shut down this bot!",delete_after=20)

  @bot.command(pass_content=True,aliases=['c','C','Clear'], help = 'Cancels current track and clears the queue')
  async def clear(ctx):
    global looping
    global waiting
    global loop_current
    global last_song
    waiting = False
    looping = False
    queue.clear()
    loop_current = False
    last_song = {}
    ctx.voice_client.stop()

  @bot.command(pass_content=True,aliases=['p'], help = 'Plays music from YouTube. Can take a url or a song title. Also used to choose search result when specified')
  async def play(ctx, *,query=None):
    global playlist
    global waiting
    if query == None:
      await ctx.send(content=f"{ctx.message.author.name}: You must enter a song name or url",delete_after=20)
    else:
      joined = await join(ctx)
      if joined:
        if waiting and (query == "1" or query =="2" or query=="3" or query == "4" or query == "5"):
          selected_song = int(query)-1
          waiting = False
          song = {
                  'url': playlist[selected_song]['url'],
                  'title': playlist[selected_song]['title'],
                  'duration': playlist[selected_song]['duration'],
                }
          await play_song(ctx,song)
        else:
          message = await ctx.send(content=":hourglass: searching")
          YDL_OPTIONS = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch5',
            'postprocessors': [{
              'key': 'FFmpegExtractAudio',
              'preferredcodec': 'mp3',
              'preferredquality': '196',
            }],
          }
          with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
              info = ydl.extract_info(query, download=False)
              if not 'entries' in info:
                await ctx.message.delete()
                song = {
                  'url': info['formats'][0]['url'],
                  'title': info['title'],
                  'duration': info['duration'],
                }
                await message.delete()
                await play_song(ctx,song)
              else:
                if len(info['entries']) == 0:
                  await ctx.send(content="Couldn't find anything matching this search, please try a more general query",delete_after=20)
                elif len(info['entries']) <= 5:
                  waiting = True
                  i = 0
                  await message.edit(content = "**Please select a track to play with ``-p 1-5`` command:**")
                  playlist = []
                  for entry in info["entries"]:
                    playlist.append({
                      'url': entry['formats'][0]['url'],
                      'title': entry['title'],
                      'duration': entry['duration']
                    })
                    converted_duration = await convert_duration(entry['duration'])
                    await message.edit(content = f"{message.content} \n**{i+1}**: {playlist[i]['title']} ({converted_duration})")
                    i += 1
                elif len(info['entries']) > 5:
                  await ctx.send("**Detected playlist... adding to queue**")
                  for entry in info['entries']:
                    song = {
                      'url': entry['formats'][0]['url'],
                      'title': entry['title'],
                      'duration': entry['duration'],
                    }
                    await play_song(ctx,song)

  @bot.command(pass_content=True,aliases=['t','T','Toggle'], help = 'Toggles on or off the current music playing ')
  async def toggle(ctx):
    vc = ctx.voice_client
    if vc.is_paused():
      vc.resume()
      await ctx.send(content="**Resuming**",delete_after=20)
    elif vc.is_playing():
      vc.pause()
      await ctx.send(content="**Paused**",delete_after=20)

  @bot.command(pass_content=True,aliases=['j','J','Join'], help = "Makes the bot join your current voice channel. It won't play music")
  async def join(ctx):
    if not ctx.message.author.voice:
      await ctx.send(content=f"{ctx.message.author.name}: You must join a voice channel first",delete_after=20)
      return False
    else:
      channel = ctx.message.author.voice.channel
      bot_voice = ctx.voice_client
      if bot_voice:
        await bot_voice.move_to(channel)
        return True
      else:
        await channel.connect()
        return True
    
  @bot.command(pass_content=True,aliases=['l','L','Leave'], help = 'Disconnects the bot from the current voice channel')
  async def leave(ctx):
    for server_voice_client in ctx.bot.voice_clients:
      if server_voice_client.guild == ctx.message.guild:
        await server_voice_client.disconnect()

  @bot.command(help = 'Displays credits')
  async def credits(ctx):
    await ctx.send("Created by Ryan Maxin")
except Exception as e:
  print(e)

bot.run(password)