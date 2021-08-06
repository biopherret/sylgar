import discord
import logging
from discord.ext import commands
import random

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

token_file = open('/home/bots/sylgar/sylgar_token.txt', 'r')
token = token_file.read()

intents = discord.Intents.default()
intents.members = True

client = commands.Bot(command_prefix = '.', intents = intents)
client.remove_command('help')

#Guild (server) ID
guild_id = 501576507580219392

#Role IDs##
club_officer_id = 504109818382909482
bots_id = 562386661288443919

@client.event
async def on_ready():
    bot_description = discord.Game('Just Swimming | .help')
    await client.change_presence(activity = bot_description)
    print('We have logged in as {0.user}'.format(client))

@client.command()
async def help(ctx):
    embed = discord.Embed(title = 'Commands for Sylgar', description = 'Begin the command with "." followed by the name of the command')
    embed.add_field(name = 'books', value = 'To get a link to a bunch of 5e Books')
    embed.add_field(name = 'disclaimer', value = 'Get a random disclaimer from a 5e Book')
    await ctx.send(embed = embed)

@client.command()
async def books(ctx):
    await ctx.send('Folder of 5e books: https://drive.google.com/open?id=1kBYin1h9wUBaaWaPaM3U8HBaC8hDaIgJ')

@client.command()
async def disclaimer(ctx):
    disclaimers = [
        'Monster Manual Disclaimer: Any similarities between monsters depicted in this book and monsters that actually exist are purely coincidental. That goes double for mind flayers, which absolutely, utterly, and completely do not exist, nor do they secretly run the D&D team. Do we really need a disclaimer to tell you that? You shouldn’t use your brain to consider such irrational thoughts. They only make the mind cluttered, confused, and unpleasantly chewy. A good brain is nice, tender, and barely used. Go ahead, put down this book and watch some reality TV or Internet cat videos. They’re really funny these days. You won’t regret it. We say this only because we love you and your juicy, succulent gamer brain.',
        'Players Handbook Disclaimer: Wizards of the Coast is not responsible for the consequences of splitting up the team, sticking appendages in the mouth of a leering green devil face, accepting a dinner invitation from bugbears, storming the feast hall of a hill giant steading, angering a dragon of any variety, or saying yes when the DM asks, "Are you really sure?"',
        'Dungeon Masters Guide Disclaimer: Wizards of the Coast does not officially endorse the following tactics ... First, always keep a straight face and say OK no matter how ludicrous or doomed the players’ plan of action is. Second, no matter what happens, pretend that you intended all along for everything to unfold the way it did. Third, if you’re not sure what to do next, feign illness, end the session early, and plot your next move. When all else fails, roll a bunch of dice behind your screen, study them for a moment with a look of deep concern mixed with regret, let loose a heavy sigh, and announce that Tiamat swoops from the sky and attacks.',
        'Hoard of the Dragon Queen Disclaimer: The following adventure contains chromatic dragons. Wizards of the Coast cannot be held liable for characters who are incinerated, dissolved, frozen, poisoned, or electrocuted.',
        'Rise of Tiamat Disclaimer: Tiamat does not apologize for TPKs.',
        'Tomb of Annihilation Disclaimer: This adventure will make your players hate you — The kind of simmering hatred that eats away at their sounds until all that remains are dark little spheres of annihilation where their hearts used to be. PS Don’t forget to tear up their character sheets',
        "Sword Coast Adventures Guide Disclaimer: Wizards of the Coast cannot be held responsible for any actions undertaken by entities native to or currently inhabiting the Forgotten Realms, including necromancer lords of distant magocracies, resident mages of any or all Dales but especially Shadowdale, drow rangers wielding one or more scimitars and accompanied by one or more panthers, mad wizards inhabiting sprawling dungeons accessible via a well in the middle of a tavern, beholders who head up criminal cartels, and anyone with the word Many-Arrows in their name. In the event of a catastrophic encounter with any or all such entities, blame your Dungeon Master. If that doesn't work, blame Ed Greenwood, but don't tell him we told you that. He knows more archmages than we do",
        "Volo's Guide to Monsters Disclaimer: Wizards of the Coast does not vouch for, guarantee, or provide any promise regarding the validity of the information provided in this volume by Volothamp Geddarm. Do not trust Volo. Do not go on quests offered by Volo. Do not listen to Volo. Avoid being seen with him for risk of guilt by association. If Volo appears in your campaign, your DM is undoubtedly trying to kill your character in a manner that can be blamed on your own actions. The DM is probably trying to do that anyway, but with Volo's appearance, you know for sure. We're not convinced that Elminster's commentary is all that trustworthy either, but he turned us into flumphs the last time we mentioned him in one of these disclaimers.",
        "Xanathar's Guide to Everything Disclaimer: No goldfish were harmed in the making of this book. Especially not Sylgar. Sylgar definitely did not die because we forgot to change his water. If you see Xanathar, make sure it knows that. Be perfectly clear Sylgar was not harmed. And we had nothing to do with it. Better yet, don't bring it up, and don't mention us."
    ]
    await ctx.send(random.choice(disclaimers))

@client.command()
@commands.has_any_role(club_officer_id)
async def helpA(ctx):
    embed = discord.Embed(title = 'Commands Only for Club Officers', description = 'Begin the command with "." followed by the name of the command')
    embed.add_field(name = 'NewGame', value = 'Creates a new game.\nUse format .NewGame <one-word-game-name> <#Hex Color Code> @<The Game Master>')
    await ctx.send(embed = embed)

@client.command()
@commands.has_any_role(club_officer_id)
async def NewGame(ctx, name, color : discord.Color, game_master : discord.Member):
    guild = ctx.guild
    world_channel_name = '{}-world-info'.format(name)
    bot_channel_name = '{}-bot-jail'.format(name)
    voice_channel_name = '{} Voice'.format(name)

    #Creates a new role
    new_role = await guild.create_role(name = name, color = color)
    #Find bots role
    bots = guild.get_role(bots_id)
    #Creates a category
    category = await guild.create_category(name = name)

    #Channel permition overwrites
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages = False, connect = False),
        new_role: discord.PermissionOverwrite(read_messages = True, send_messages = True, connect = True, read_message_history = True),
        bots: discord.PermissionOverwrite(read_messages = True, send_messages = True, connect = True, read_message_history = True)
    }
    world_overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages = False, connect = False),
        new_role: discord.PermissionOverwrite(read_messages = True, send_messages = False, connect = True, read_message_history = True),
        game_master: discord.PermissionOverwrite(read_messages = True, send_messages = True, connect = True, read_message_history = True)
    }

    #Creates text and voice channels
    await guild.create_text_channel(name = name, category = category, overwrites = overwrites)
    await guild.create_text_channel(name = world_channel_name, category = category, overwrites = world_overwrites)
    await guild.create_text_channel(name = bot_channel_name, category = category, overwrites = overwrites)
    await guild.create_voice_channel(name = voice_channel_name, category = category, overwrites = overwrites)

client.run(token)
