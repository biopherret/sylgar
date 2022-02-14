from distutils import command
import discord
import logging, json, asyncio
from discord.ext import commands
from time import time
import random
import datetime, pytz

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

#Role IDs
club_officer_id = 504109818382909482
game_master_id = 501769599876857857
bots_id = 562386661288443919
new_member_role_id = 635867613133799424
club_member_role_id = 633145437418946570

#channel IDs
adventure_channel_id = 890622962544304258
sus_channel_id = 926625097383551056
officer_bot_channel_id = 926625264593682452
sus_approvals_channel_id = officer_bot_channel_id
gm_bot_channel_id = 926625351621308466
introductions_channel_id = 633127328108511262
officer_channel_id = 704157952948305922

#message IDs
sus_message_id = 926625686251249715

#member IDs
bot_member_id = 823039502179631144

async def write_json(data, file_name):
    with open (file_name, 'w') as file:
        json.dump(data, file, indent = 4)

async def open_json(file_name):
    with open (file_name) as file:
        return json.load(file)

#functions needed for sign up sheet
async def find_reacting_users(channel_id : int, message_id : int, valid_reactions : dict):
    '''Returns a dict of lists of user ids (whose keys are the name assigned in the valid_reactions dict), does not include the bot user
    channel_id: channel id of the channel contaning message being reacted to
    message_id: message id of the message being reacted to
    valid_reaction: (optional) dictionary whose keys are names, and values are the related emoji'''
    reacting_users = {}
    channel = await client.fetch_channel(channel_id)
    message = await channel.fetch_message(message_id)

    for i in range(len(message.reactions)):
        users = []
        emoji = str(message.reactions[i])
        if emoji in list(valid_reactions.values()): #if the emoji is valid
            name = list(valid_reactions.keys())[list(valid_reactions.values()).index(emoji)]
            async for user in message.reactions[i].users():
                if user.id != bot_member_id:
                    users.append(user.id)

            reacting_users[name] = users

    return reacting_users

async def reactions_added(previous_reacting_users : dict, current_reacting_users : dict):
    '''previous_reacting_users and current_reacting_users are each a dict of lists of user ids
    Returns a dict of lists of user_ids who added a reaction'''
    #Ingore any keys that have been removed or added
    previous_reacting_users_ignore_key_change = {}
    for name in previous_reacting_users:
        if name in current_reacting_users:
            previous_reacting_users_ignore_key_change[name] = previous_reacting_users[name]
    current_reacting_users_ignore_key_change = {}
    for name in current_reacting_users:
        if name in previous_reacting_users:
            current_reacting_users_ignore_key_change[name] = current_reacting_users[name]

    added_users = {}
    for name in current_reacting_users_ignore_key_change: #for each reaction
        users = []
        for user_id in current_reacting_users_ignore_key_change[name]: #for each user
            if user_id not in previous_reacting_users_ignore_key_change[name]: #if a current reacting user had not reacted perviously
                users.append(user_id)

        added_users[name] = users

    return added_users

async def reactions_removed(previous_reacting_users : dict, current_reacting_users : dict):
    '''previous_reacting_users and current_reacting_users are each a dict of lists of user ids
    Returns a dict of lists of user_ids who removed a reaction'''
    #Ingore any keys that have been removed or added
    previous_reacting_users_ignore_key_change = {}
    for name in previous_reacting_users:
        if name in current_reacting_users:
            previous_reacting_users_ignore_key_change[name] = previous_reacting_users[name]
    current_reacting_users_ignore_key_change = {}
    for name in current_reacting_users:
        if name in previous_reacting_users:
            current_reacting_users_ignore_key_change[name] = current_reacting_users[name]

    removed_users = {}
    for name in previous_reacting_users_ignore_key_change: #for each reaction
        users = []
        for user_id in previous_reacting_users_ignore_key_change[name]: #for each user
            if user_id not in current_reacting_users_ignore_key_change[name]: #if a pervious reacting is not currently reacting
                users.append(user_id)

        removed_users[name] = users

    return removed_users

async def add_to_game(user_id : int, game_name : str):
    '''Adds player data to sign up sheet file and gives user appropriate role
    user: user_id, the user being added to the game
    game: str, name of the game as listed on the sign up sheet'''

    guild = client.get_guild(guild_id)
    member = guild.get_member(user_id)

    data = await open_json('sign_up_sheet.json')
    game_data = data[game_name]

    #add player id to the game file
    data[game_name]['player_ids'].append(user_id)
    await write_json(data, 'sign_up_sheet.json')

    #give player the role
    await member.add_roles(guild.get_role(game_data['role_id']))

    #update the sign up sheet message
    await update_sus()

async def remove_from_game(user_id : int, game_name : str):
    '''Removes player data from sign up sheet file and removes the appropriate role
    user: discord user object, the user being removed from the game
    game: str, name of the game as listed on the sign up sheet'''

    guild = client.get_guild(guild_id)
    member = guild.get_member(user_id)

    data = await open_json('sign_up_sheet.json')
    game_data = data[game_name]

    #remove player id from game file
    data[game_name]['player_ids'].remove(user_id)
    await write_json(data, 'sign_up_sheet.json')

    #take away the role
    await member.remove_roles(guild.get_role(game_data['role_id']))

    #update the sign up sheet message
    await update_sus()

async def get_open_games():
    '''Returns a list of game names which are listed on the sign up sheet and have open spots'''
    data = await open_json('sign_up_sheet.json')
    open_games = []

    for game_name in data:
        game_data = data[game_name]
        open_spots = game_data['max_players'] - len(game_data['player_ids'])
        #don't include games not listed on signup sheet or with no open spots
        if game_data['on_sus'] == 'yes' and (open_spots > 0):
            open_games.append(game_name)

    return open_games

async def get_open_game_reactions(open_games : list):
    '''open_games: list of game names which are listed on the sign up sheet and have open spots
    Returns a dictionary whose keys are game names, and values are the related emoji'''
    data = await open_json('sign_up_sheet.json')
    open_game_reactions = {}
    for game_name in open_games:
        game_data = data[game_name]
        open_game_reactions[game_name] = game_data['reaction']

    return open_game_reactions

async def get_sus_card(game_name):
    '''Generates the sign up sheet string for a single game, regardless of if the game would be added to the sign up sheet
    game: str, name of game'''
    data = await open_json('sign_up_sheet.json')
    game_data = data[game_name]
    dm = await client.fetch_user(game_data['dm_id'])
    open_spots = game_data['max_players'] - len(game_data['player_ids'])

    sus_game_card = '__{}__ {}\nGame Master: {}\nOpen Spots: {}\n{}'.format(game_name, game_data['reaction'], dm.mention, open_spots, game_data['description'])

    return sus_game_card

async def get_sus():
    '''Generates the sign up sheet str for all listed games with open spots'''
    #sus message title
    sus_message = '__**Sign Up Sheet**__'

    open_games = await get_open_games()
    for game_name in open_games:
        game_card = await get_sus_card(game_name)
        sus_message += '\n\n{}'.format(game_card)

    if sus_message == '__**Sign Up Sheet**__': #if there are no listed games with open spots
        sus_message += '\n\nUnfortunately there are currently no open game spots. If you would like to run a game reach out to a Club Officer!'

    return sus_message

async def update_sus():
    '''Updates the sign up sheet message'''
    open_games = await get_open_games()
    game_reactions = await get_open_game_reactions(open_games)
    reactions_list = list(game_reactions.values())

    sus_channel = client.get_channel(sus_channel_id)
    sus = await sus_channel.fetch_message(sus_message_id)

    for old_reaction in sus.reactions: #remove reactions for games no longer on sus
        if str(old_reaction) not in reactions_list:
            async for user in old_reaction.users():
                await sus.remove_reaction(old_reaction, client.get_guild(guild_id).get_member(user.id))

    for reaction in reactions_list: #add reactions for games added to sus
        await sus.add_reaction(reaction)

    new_sus_message = await get_sus() #get str for now sus
    await sus.edit(content = new_sus_message)

async def check_valid_game_name(name : str):
    '''Checks if game name is less than 45 characters and not allready taken
    name: str, game name
    Returns bool'''

    data = await open_json('sign_up_sheet.json')

    if len(name) <= 45 and (name not in data):
        return True
    else:
        return False

async def check_valid_description(description : str):
    '''Checks if game description is less than 1000 characters
    description: str
    returns bool'''

    if len(description) <= 1000:
        return True
    else:
        return False

async def check_valid_emoji(emoji_to_check):
    '''Checks if an emoji has not been used before and is a custom emoji on the server'''
    all_server_emojis = list(client.get_guild(guild_id).emojis)
    available_emojis = []
    for emoji in all_server_emojis:
        available_emojis.append(str(emoji))

    data = await open_json('sign_up_sheet.json')

    for game_name in data:
        available_emojis.remove(str(data[game_name]['reaction']))

    for emoji in available_emojis:
        if str(emoji_to_check) == str(emoji):
            return True
        else:
            continue

    return False

async def check_if_club_officer(user_id : int):
    '''Checks if a member is a club officer'''
    guild = client.get_guild(guild_id)
    member = guild.get_member(user_id)
    for role in member.roles:
        if role.id == club_officer_id:
            return True
    return False

async def officer_approve(ctx, message : str):
    '''Sends an approval message in the approvals channel
    message: str describing the request
    Returns true or false once one officer reacts to the message.'''
    sus_approvals_channel = ctx.bot.get_channel(sus_approvals_channel_id)
    approval_message = await sus_approvals_channel.send('Please approve or deny the following request (will timeout after an hour and reject the aproval):\n{}'.format(message))
    await approval_message.add_reaction('🟩')
    await approval_message.add_reaction('🟥')

    current_time = time()
    end_time = current_time + 3600

    while current_time < end_time:
        use_message = await approval_message.channel.fetch_message(approval_message.id)
        if use_message.reactions[0].count > 1:
            return True
        elif use_message.reactions[1].count > 1:
            return False

    return False

async def user_confirm(user_id, message):
    '''DMs a user a confirmation message
    user_id: int id of the user who needs to confirm the action
    message: str describing the action that needs to be confirmed
    Returns true of false once the user reacts to the message.'''
    user = client.get_user(user_id)
    confirm_message = await user.send(message)
    await confirm_message.add_reaction('🟩')
    await confirm_message.add_reaction('🟥')

    current_time = time()
    end_time = current_time + 3600

    while current_time < end_time:
        use_message = await confirm_message.channel.fetch_message(confirm_message.id)
        if use_message.reactions[0].count > 1:
            return True
        elif use_message.reactions[1].count > 1:
            return False

    return False

#help commands
@client.group(invoke_without_command = True)
async def help(ctx):
    embed = discord.Embed(title = 'How to use Sylgar', description = 'Type .help `command` to get more information about the command.')
    embed.add_field(name = 'member', value = 'See all commands available to club members')
    embed.add_field(name = 'GM', value = 'See all commands available to game master, including signup sheet and game management')
    await ctx.send(embed = embed)

@help.command()
async def member(ctx):
    embed = discord.Embed(title = 'Member Commands', description = 'All commands begin with "."')
    embed.add_field(name = '.books', value = 'To get a link to a bunch of 5e Books')
    embed.add_field(name = '.disclaimer', value = 'Get a random disclaimer from a 5e Book')
    embed.add_field(name = '.about', value = 'Get a link to the github for this bot to see its code')
    await ctx.send(embed = embed)

@help.command()
async def officer(ctx):
    embed = discord.Embed(title = 'Officer Commands', description = 'All commands begin with "."')
    embed.add_field(name = '.force_sus_update', value = 'Forces the sign up sheet message to update, use if the sign up sheet file was changed manually.', inline = False)
    embed.add_field(name = '.add_game_data', value = 'Add a game to sign up sheet file (dose not change the server)\nUse Format: .add_game_data <game name with dashes for spaces> <game listing status> <max players> <reaction> <@game master> <@role> <category id> <description>', inline = False)
    embed.add_field(name = '.remove_game_data', value = 'Remove game from sign up sheet file (dose not change the server)\nUse Format: .remove_game_data <game name with dashes for spaces>', inline = False)
    embed.add_field(name = '.add_player_data', value = 'Add player data to sign up sheet file (dose not change the server)\nUse Format: .add_player_data <game name with dashes for spaces> <@player>', inline = False)
    embed.add_field(name = '.remove_player_data', value = 'Remove player data from the sign up sheet file (dose not change the server)\nUse Format: .remove_player_data <game name with dashes for spaces> <@player>', inline = False)
    await ctx.send(embed = embed)

@help.command()
async def GM(ctx):
    embed = discord.Embed(title = 'Game Master Commands', description = 'All commands begin with "."')
    embed.add_field(name = '.create_game', value = 'Create a game on the server\nUse Format: .create_game <game name with dashes for spaces> <game listing status> <max players> <reaction> <@game master> <description>', inline = False)
    embed.add_field(name = '.add_player', value = 'Add a player to your game\nUse Format: .add_player <game name with dashes for spaces> <@player>', inline = False)
    embed.add_field(name = '.remove_player', value = 'Remove a player from your game\nUse Format: .remove_player <game name with dashes for spaces> <@player>', inline = False)
    embed.add_field(name = '.remove_game', value = 'Remove your game from the server\nUse Format: .remove_game <game name with dashes for spaces>', inline = False)
    embed.add_field(name = '.see_game_status', value = 'See the status and stored info of your game\nUse Format .see_game_status <game name with dashes for spaces>', inline = False)
    embed.add_field(name = '.see_all_games', value = 'See a list of the names of all current games in the club', inline = False)
    embed.add_field(name = '.see_available_emojis', value = 'See a list of all available emojis which could be used as a reaction for the sign up sheet', inline = False)
    embed.add_field(name = '.edit_game_name', value = 'Edit the name of your game\nUse Format: .edit_game_name <old game name with dashes for spaces> <new game name with dashes for spaces>', inline = False)
    embed.add_field(name = '.edit_game_listing_status', value = 'Use "yes" if you want your game to automatically be on the sign up sheet, or "no" if not\nUse Format: .edit_game_listing_status <game name with dashes for spaces> <desired game listing status>', inline = False)
    embed.add_field(name = '.edit_max_players', value = 'Edit number of max players in your game\nUse Format: .edit_max_players <game name with dashes for spaces> <max players>', inline = False)
    embed.add_field(name = '.edit_game_reaction', value = 'Edit the emoji used for your game on the sign up sheet\nUse Format: <game name with dashes for spaces> <emoji>', inline = False)
    embed.add_field(name = '.edit_game_description', value = 'Edit the description for your game\nUse Format: .edit_game_description <game name with dashes for spaces> <description>', inline = False)
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
async def about(ctx):
    await ctx.send("This bot's github page: https://github.com/sarahalexw/sylgar")

@client.command()
@commands.has_any_role(club_officer_id)
async def add_event(ctx, event_name : str, event_time : str):
    try:
        datetime.datetime.strptime(event_time, '%m-%d-%Y %I:%M%p')
    except:
        datetime.datetime.strptime(event_time, '%m/%d/%Y %I:%M%p')
    if ctx.channel.id != officer_channel_id:
        await ctx.message.delete()
        await ctx.send(f'Sorry please do not use this channel for creating events. Please use {client.get_channel(officer_channel_id).mention}', delete_after = 5)
        return
    await ctx.reply('*You have 10 minutes to make any edits before the event is submitted*')
    original_message = ctx.message
    release = ctx.message.created_at.now(pytz.timezone('US/Pacific')).replace(tzinfo = None) + datetime.timedelta(0,600) # 600secs = 10 minutes
    while datetime.datetime.now(pytz.timezone('US/Pacific')).replace(tzinfo = None) < release:
        await asyncio.sleep(1)
        edit_message_time = original_message.edited_at
        if not edit_message_time: #if the message was never edited
            pass
        else:
            list_of_messages = ctx.message.content.split('"')
            event_time = list_of_messages[3]
            event_name = list_of_messages[1]
            try:
                datetime.datetime.strptime(event_time, '%m-%d-%Y %I:%M%p')
            except:
                datetime.datetime.strptime(event_time, '%m/%d/%Y %I:%M%p')
        data = await open_json('Bot_Info.json')
        data["event"].append({"date" : event_time, "event-name": event_name})
        await write_json(data, 'Bot_Info.json')

@add_event.error
async def error_add_event(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("Sorry you don't have the required Role to use that command, to view your available commands use `.help`")
    elif isinstance(error, commands.MissingRequiredArgument):
        if ctx.channel.id != officer_channel_id:
            await ctx.message.delete()
            await ctx.send(f'Sorry please do not use this channel for creating event reminders. Please use {client.get_channel(officer_channel_id).mention}', delete_after = 5)
        else:
            await ctx.send("Please enter all arguments. To get more information about this command use `.help events`")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"Sorry I couldn't add that event. Please use the correct format for events. Use `.help events` to get more information.\n{error}")
    elif isinstance(error, commands.UnexpectedQuoteError):
        await ctx.send(f'Looks like there was a quote error.\n{error}')

@commands.command()
@commands.has_any_role(club_officer_id)
async def events(ctx):
    if ctx.channel.id != officer_bot_channel_id:
        await ctx.message.delete()
        await ctx.send(f'Sorry please do not use this channel for viewing events. Please use {client.get_channel(officer_channel_id).mention}', delete_after = 5)
        return
    else:
        events = await open_json('Bot_Info.json')
        embed = discord.Embed(title = 'Events', description = '', colour = 0X003560, timestamp = datetime.datetime.now(datetime.timezone.utc)) 
        for event in events["event"]:
            embed.add_field(name = event["event-name"], value = f'Date: {event["date"]}')
        await ctx.send(embed = embed)

#Adventure commands
@client.command()
async def atlas(ctx):
    guild = client.get_guild(guild_id)
    adventure_channel = guild.get_channel(adventure_channel_id)
    user_name = ctx.author
    if isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send('Flame slain brings the darkness of night, find the flame that sheds eternal light.')
        await adventure_channel.send('{} has found the the first cipher!'.format(user_name))
    else:
        await ctx.message.delete()
        await ctx.send("Please only use the adventure commands in the bot's DMs")

@client.command()
async def torch(ctx):
    guild = client.get_guild(guild_id)
    adventure_channel = guild.get_channel(adventure_channel_id)
    user_name = ctx.author
    if isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send('A great cobbled loop full of mechanical beasts, as Patrick Star would say you should head NorthWeest.')
        await adventure_channel.send('{} has found the the second cipher!'.format(user_name))
    else:
        await ctx.message.delete()
        await ctx.send("Please only use the adventure commands in the bot's DMs")

@client.command()
async def journey(ctx):
    guild = client.get_guild(guild_id)
    adventure_channel = guild.get_channel(adventure_channel_id)
    user_name = ctx.author
    if isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send("You're halfway done through your quest, you deserve a break, find the place where students can snack and rest.")
        await adventure_channel.send('{} has found the the third cipher!'.format(user_name))
    else:
        await ctx.message.delete()
        await ctx.send("Please only use the adventure commands in the bot's DMs")

@client.command()
async def tavern(ctx):
    guild = client.get_guild(guild_id)
    adventure_channel = guild.get_channel(adventure_channel_id)
    user_name = ctx.author
    if isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send("Many before you have reflected at this location. Seek it under an obelisk's shadow.")
        await adventure_channel.send('{} has found the the fourth cipher!'.format(user_name))
    else:
        await ctx.message.delete()
        await ctx.send("Please only use the adventure commands in the bot's DMs")

@client.command()
async def rest(ctx):
    guild = client.get_guild(guild_id)
    adventure_channel = guild.get_channel(adventure_channel_id)
    user_name = ctx.author
    if isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send("Call the underground meeting place what you want: an adventurers' guild, a tavern, what have you - but know this is a place of  great social power.")
        await adventure_channel.send('{} has found the the fifth cipher!'.format(user_name))
    else:
        await ctx.message.delete()
        await ctx.send("Please only use the adventure commands in the bot's DMs")

@client.command()
async def nexus(ctx):
    guild = client.get_guild(guild_id)
    adventure_channel = guild.get_channel(adventure_channel_id)
    user_name = ctx.author
    if isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send('Under bulbous illuminators lies a peaceful clearing; many ents and their kin reside here. Here, wizards and artificers study matters of the human race.')
        await adventure_channel.send('{} has found the the sixth cipher!'.format(user_name))
    else:
        await ctx.message.delete()
        await ctx.send("Please only use the adventure commands in the bot's DMs")

@client.command()
async def connect(ctx):
    guild = client.get_guild(guild_id)
    adventure_channel = guild.get_channel(adventure_channel_id)
    user_name = ctx.author
    if isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send('The strongest among them come here to pilot the great ships of the fleet.')
        await adventure_channel.send('{} has found the the seventh cipher!'.format(user_name))
    else:
        await ctx.message.delete()
        await ctx.send("Please only use the adventure commands in the bot's DMs")

@client.command()
async def wild(ctx):
    guild = client.get_guild(guild_id)
    adventure_channel = guild.get_channel(adventure_channel_id)
    user_name = ctx.author
    if isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send('Congratulations you have found the last cipher! However if you have not tired of your journey yet, there lies one more bonus secret. Be warned this last quest is not for the faint of heart.\nA location of great artifice, often spoken of in hushed tones, a solitary throne that overlooks the grand expanse of the ocean.')
        await adventure_channel.send('{} has found the the eighth and last cipher!'.format(user_name))
    else:
        await ctx.message.delete()
        await ctx.send("Please only use the adventure commands in the bot's DMs")

@client.command()
async def rite(ctx):
    guild = client.get_guild(guild_id)
    adventure_channel = guild.get_channel(adventure_channel_id)
    user_name = ctx.author
    if isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send('Congratulations you have found the final cipher!')
        await adventure_channel.send('{} has found the the supper secret ninth (and actually last) cipher!'.format(user_name))
    else:
        await ctx.message.delete()
        await ctx.send("Please only use the adventure commands in the bot's DMs")

#Sign up sheet commands for DMs
@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def create_game(ctx, name : str, on_sus : str, max_players : int, reaction, game_master : discord.Member, *, description : str):
    '''Adds a new game to the sign up sheet file, creates a new role, and creates all channels for the game in new category
    name: str, the name of the game as it will be written in channels (with dashes), dashes will be replaced with spaces for sus
    on_sus: "yes" if the game is listed on the sign up sheet, "no" if not
    max_players: int, max_number of players that can sign up for the game
    reaction: str, emoji id, must be a emoji custom to the server, emoji used for reaction add
    game_master: str, @user, game master of the game
    description: str, game description which should show on the sign up sheet'''
    is_valid_name = await check_valid_game_name(name)
    is_valid_description = await check_valid_description(description)
    is_valid_emoji = await check_valid_emoji(reaction)

    author_id = ctx.author.id
    is_club_officer = await check_if_club_officer(author_id)

    if (ctx.channel.id != gm_bot_channel_id) and (ctx.channel.id != officer_bot_channel_id):
        await ctx.send('Please use the create_game command in the #gm-bot-jail text channel')
    elif author_id != game_master.id and not is_club_officer:
        await ctx.send('Sorry, you can not create a game for another game master unless you are a club officer.')
    elif not is_valid_name:
        await ctx.send('Game name must be less than 45 characters and not have the same name as another game in the club.')
    elif not is_valid_description:
        await ctx.send('Description must be less than 100 characters.')
    elif not is_valid_emoji:
        await ctx.send('Emoji must be a custom server emoji and must not be used by another game.')
    else:
        guild = ctx.guild

        #generate channel names (which cannot contian spaces)
        name_w_spaces = name.replace('-', ' ')
        world_channel_name = '{}-world-info'.format(name)
        bot_channel_name = '{}-bot-jail'.format(name)
        voice_channel_name = '{} Voice'.format(name_w_spaces)

        #Generate officer approval message and waiting message
        approve_message = 'New Game Reqest\nName: {}\nListed on sign up sheet: {}\nMax players: {}\nReaction: {}\nGame Master: {}\nDescription: {}'.format(name_w_spaces, on_sus, max_players, reaction, game_master.mention, description)
        waiting_message = 'Club officers are reviewing your game. You will be notified once the game has been approved.'

        await ctx.send(waiting_message)
        approved = await officer_approve(ctx, approve_message)
        if approved:
            #Creates a new role
            new_role = await guild.create_role(name = name_w_spaces, color = discord.Color.random())
            #Find bots role
            bots = guild.get_role(bots_id)
            #Creates a category
            category = await guild.create_category(name = name_w_spaces)

            #Channel permition overwrites
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages = False, connect = False),
                new_role: discord.PermissionOverwrite(read_messages = True, send_messages = True, connect = True, read_message_history = True),
                bots: discord.PermissionOverwrite(read_messages = True, send_messages = True, connect = True, read_message_history = True)
            }
            world_overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages = False, connect = False),
                new_role: discord.PermissionOverwrite(read_messages = True, send_messages = False, connect = True, read_message_history = True),
                bots: discord.PermissionOverwrite(read_messages = True, send_messages = True, connect = True, read_message_history = True),
                game_master: discord.PermissionOverwrite(read_messages = True, send_messages = True, connect = True, read_message_history = True)
            }

            #Creates text and voice channels
            await guild.create_text_channel(name = name, category = category, overwrites = overwrites)
            await guild.create_text_channel(name = world_channel_name, category = category, overwrites = world_overwrites)
            await guild.create_text_channel(name = bot_channel_name, category = category, overwrites = overwrites)
            await guild.create_voice_channel(name = voice_channel_name, category = category, overwrites = overwrites)

            #Gives the game master their game role
            await game_master.add_roles(new_role)

            #Adds new game to sign_up_sheet.json
            data = await open_json('sign_up_sheet.json')
            game_data = {'on_sus': on_sus,
                'dm_id': game_master.id,
                'max_players': int(max_players),
                'role_id': new_role.id,
                'category': category.id,
                'description': description,
                'reaction': reaction,
                'player_ids': []}
            data[name_w_spaces] = game_data

            await write_json(data, 'sign_up_sheet.json')

            #send message confinming game was added
            await ctx.send('{} Your game has been approved and added to the discord.'.format(game_master.mention))

            #update the sign up sheet message
            await update_sus()
        else:
            #send message saying the game was not approved
            await ctx.send('{} Your new game has been denied, an officer will message you explaining why and how to resolve the issue.'.format(game_master.mention))

@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def add_player(ctx, game_name_w_dashes : str, player : discord.Member):
    '''Command to manually add a player to a game and add them to sign up sheet file
    game_name_w_dashes: str, the name of the game as it will be written in channels (with dashes)
    player: @user, player to add'''
    author_id = ctx.author.id
    is_club_officer = await check_if_club_officer(author_id)

    data = await open_json('sign_up_sheet.json')
    game_name = game_name_w_dashes.replace('-', ' ')

    if game_name not in data:
        await ctx.send('{} is not an existing game. If the game exists on the server but not in the sign up sheet you may use .add_game_data to add the game data to the sheet.'.format(game_name))
    elif author_id != data[game_name]['dm_id'] and not is_club_officer:
        await ctx.send('Sorry, you can not manage a game for another game master unless you are a club officer.')
    else:
        await add_to_game(player.id, game_name)
        await ctx.send('{} has been added to {}.'.format(player.mention, game_name))

@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def remove_player(ctx, game_name_w_dashes: str, player : discord.Member):
    '''Command to manually remove a player from a game and remove them from the sign up sheet file
    game_name_w_dashes: str, the name of the game as it will be written in channels (with dashes)
    player: @user, player to add'''
    author_id = ctx.author.id
    is_club_officer = await check_if_club_officer(author_id)

    data = await open_json('sign_up_sheet.json')
    game_name = game_name_w_dashes.replace('-', ' ')

    if game_name not in data:
        await ctx.send('{} is not an existing game. If the game exists on the server but not in the sign up sheet you may use .add_game_data to add the game data to the sheet.'.format(game_name))
    elif author_id != data[game_name]['dm_id'] and not is_club_officer:
        await ctx.send('Sorry, you can not manage a game for another game master unless you are a club officer.')
    else:
        await remove_from_game(player.id, game_name)
        await ctx.send('{} has been removed from {}.'.format(player.mention, game_name))

@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def remove_game(ctx, game_name_w_dashes : str):
    '''Removes a game from the sign up sheet file and the discord, must be approved by the game_master in DMs
    name: str, the name of the game as it will be written in channels (with dashes)'''
    author_id = ctx.author.id
    is_club_officer = await check_if_club_officer(author_id)
    guild = client.get_guild(guild_id)

    data = await open_json('sign_up_sheet.json')
    game_name = game_name_w_dashes.replace('-', ' ')

    if (ctx.channel.id != gm_bot_channel_id) and (ctx.channel.id != officer_bot_channel_id):
        await ctx.send('Please use the remove_game command in the #gm-bot-jail text channel')
    elif game_name not in data:
        await ctx.send('{} is not an existing game. If the game exists on the server but not in the sign up sheet you may use .add_game_data to add the game data to the sheet.'.format(game_name))
    elif author_id != data[game_name]['dm_id'] and not is_club_officer:
        await ctx.send('Sorry, you can not create a game for another game master unless you are a club officer.')
    else:
        game_data = data[game_name]
        game_master_id = game_data['dm_id']
        #generate confermation message
        message = 'You, or a club officer, have requested that your game be removed, which will remove the role and all channels for your game. Please react below to confirm (or deny) this action; once you confirm this cannot be undone. This message will timeout after 1 hour and automatically deny the request.'
        confirmed = await  user_confirm(game_master_id, message)
        if confirmed:
            #remove data from json
            del data[game_name]
            await write_json(data, 'sign_up_sheet.json')

            await update_sus()

            #delete channels and category
            category = client.get_channel(game_data['category'])
            channels = category.channels
            for channel in channels:
                await channel.delete()
            await category.delete()

            role = guild.get_role(game_data['role_id'])
            await role.delete()
            await ctx.send('{} has been removed from the server'.format(game_name))
        else:
            ctx.send('Game removal has bee denied by the DM. Please confirm with {} before attempting to remove their game.'.format(guild.get_member(game_master_id)))

@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def see_game_status(ctx, game_name_w_dashes : str):
    '''Sends the current game data, as it would appear on the sign up sheet, and the current players signed up
    game_name_w_dashes: str, the name of the game as it will be written in channels (with dashes), dashes will be replaced with spaces for sus'''
    author_id = ctx.author.id
    is_club_officer = await check_if_club_officer(author_id)
    guild = client.get_guild(guild_id)

    data = await open_json('sign_up_sheet.json')
    game_name = game_name_w_dashes.replace('-', ' ')

    if game_name not in data:
        await ctx.send('{} is not an existing game. If the game exists on the server but not in the sign up sheet you may use .add_game_data to add the game data to the sheet.'.format(game_name))
    elif author_id != data[game_name]['dm_id'] and not is_club_officer:
        await ctx.send('Sorry, you can not manage a game for another game master unless you are a club officer.')
    else:
        message = await get_sus_card(game_name)
        message += '\nListed on Signup Sheet?: {}'.format(data[game_name]['on_sus'])
        message += '\n\n*Current Players*:'
        for player_id in data[game_name]['player_ids']:
            member = guild.get_member(player_id)
            message += '\n{}'.format(member.name)

        await ctx.send(message)

@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def see_all_games(ctx):
    '''Sends the names of the names of all games in the club'''
    data = await open_json('sign_up_sheet.json')
    message = 'All Games in the Club:'
    for game_name in data:
        message += '\n{}'.format(game_name)

    await ctx.send(message)

@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def see_available_emojis(ctx):
    '''Sends a list of all available emojis which can be used for game reactions'''
    all_server_emojis = list(client.get_guild(guild_id).emojis)
    available_emojis = []
    for emoji in all_server_emojis:
        available_emojis.append(str(emoji))

    data = await open_json('sign_up_sheet.json')

    for game_name in data:
        available_emojis.remove(str(data[game_name]['reaction']))

    message = 'Available Emojis (if you would like to use another emoji DM an officer and we can add an emoji to the server)\n'

    for emoji in available_emojis:
        message += emoji

    await ctx.send(message)

@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def edit_game_name(ctx, old_game_name_w_dashes : str, new_game_name_w_dashes : str):
    '''Edits the game name in both bot data and on the discord
    game_name_w_dashes: str, the name of the game as it will be written in channels (with dashes)'''
    author_id = ctx.author.id
    is_club_officer = await check_if_club_officer(author_id)
    guild = client.get_guild(guild_id)

    data = await open_json('sign_up_sheet.json')
    old_game_name = old_game_name_w_dashes.replace('-', ' ')

    if old_game_name not in data:
        await ctx.send('{} is not an existing game. If the game exists on the server but not in the sign up sheet you may use .add_game_data to add the game data to the sheet.'.format(old_game_name))
    elif author_id != data[old_game_name]['dm_id'] and not is_club_officer:
        await ctx.send('Sorry, you can not manage a game for another game master unless you are a club officer.')
    else:
        game_data = data[old_game_name]
        new_game_name = new_game_name_w_dashes.replace('-', ' ')

        message = 'Edit Game Name Request\nOld Game Name: {}\nNew Game Name:{}'.format(old_game_name, new_game_name)
        approved = await officer_approve(ctx, message)
        if approved:
            category = client.get_channel(game_data['category'])
            channels = category.channels
            for channel in channels:
                old_channel_name = channel.name
                if old_channel_name == old_game_name_w_dashes.lower():
                    new_channel_name = new_game_name_w_dashes.lower()
                elif old_channel_name == old_game_name_w_dashes.lower() + '-world-info':
                    new_channel_name = new_game_name_w_dashes.lower() + '-world-info'
                elif old_channel_name == old_game_name_w_dashes.lower() + '-bot-jail':
                    new_channel_name = new_game_name_w_dashes.lower() + '-bot-jail'
                elif old_channel_name == old_game_name + ' Voice':
                    new_channel_name = new_game_name + ' Voice'
                else:
                    await ctx.send('The channel {} does not follow expected nameing conventions and will need to be renamed manually'.format(old_channel_name))
                    continue

                await channel.edit(name = new_channel_name)

            await category.edit(name = new_game_name)

            role = guild.get_role(game_data['role_id'])
            await role.edit(name = new_game_name)

            data[new_game_name] = data.pop(old_game_name)
            await write_json(data, 'sign_up_sheet.json')

            await update_sus()

            await ctx.send('{} has been renamed to {}'.format(old_game_name, new_game_name))
        else:
            #send message saying the game was not approved
            game_master = guild.get_member(data[old_game_name]['dm_id'])
            await ctx.send('{} Your edit request has been denied, an officer will message you explaining why and how to resolve the issue.'.format(game_master.mention))

@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def edit_game_listing_status(ctx, game_name_w_dashes : str, on_sus : str):
    '''Edits on on_sus value
    game_name_w_dashes: str, the name of the game as it will be written in channels (with dashes)
    on_sus: "yes" if the game is listed on the sign up sheet, "no" if not'''
    author_id = ctx.author.id
    is_club_officer = await check_if_club_officer(author_id)

    data = await open_json('sign_up_sheet.json')
    game_name = game_name_w_dashes.replace('-', ' ')

    if game_name not in data:
        await ctx.send('{} is not an existing game. If the game exists on the server but not in the sign up sheet you may use .add_game_data to add the game data to the sheet.'.format(game_name))
    elif author_id != data[game_name]['dm_id'] and not is_club_officer:
        await ctx.send('Sorry, you can not manage a game for another game master unless you are a club officer.')
    else:
        if on_sus == 'yes' or on_sus == 'no':
            data[game_name]['on_sus'] = on_sus
            await write_json(data, 'sign_up_sheet.json')
            await update_sus()
            if on_sus == 'yes':
                await ctx.send('{} is listed on the signup sheet'.format(game_name))
            else:
                await ctx.send('{} is not listed on the signup sheet'.format(game_name))
        else:
            await ctx.send('Invalid input, please use ether "yes" or "no" do designate signup sheet listing status.')

@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def edit_max_players(ctx, game_name_w_dashes : str, max_players : int):
    '''Edits max number of players
    game_name_w_dashes: str, the name of the game as it will be written in channels (with dashes)'''
    author_id = ctx.author.id
    is_club_officer = await check_if_club_officer(author_id)

    data = await open_json('sign_up_sheet.json')
    game_name = game_name_w_dashes.replace('-', ' ')

    if game_name not in data:
        await ctx.send('{} is not an existing game. If the game exists on the server but not in the sign up sheet you may use .add_game_data to add the game data to the sheet.'.format(game_name))
    elif author_id != data[game_name]['dm_id'] and not is_club_officer:
        await ctx.send('Sorry, you can not manage a game for another game master unless you are a club officer.')
    else:
        if type(max_players) == int:
            data[game_name]['max_players'] = max_players
            await write_json(data, 'sign_up_sheet.json')
            await update_sus()
            await ctx.send('The max number of players for {} is {}'.format(game_name, max_players))
        else:
            await ctx.send('Max players must be an integer')

@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def edit_game_reaction(ctx, game_name_w_dashes : str, reaction):
    author_id = ctx.author.id
    is_club_officer = await check_if_club_officer(author_id)

    data = await open_json('sign_up_sheet.json')
    game_name = game_name_w_dashes.replace('-', ' ')

    if game_name not in data:
        await ctx.send('{} is not an existing game. If the game exists on the server but not in the sign up sheet you may use .add_game_data to add the game data to the sheet.'.format(game_name))
    elif author_id != data[game_name]['dm_id'] and not is_club_officer:
        await ctx.send('Sorry, you can not manage a game for another game master unless you are a club officer.')
    else:
        is_valid_emoji = await check_valid_emoji(reaction)
        if is_valid_emoji:
            data[game_name]['reaction'] = reaction
            await write_json(data, 'sign_up_sheet.json')
            await update_sus()
            await ctx.send('The reaction emoji for {} is {}'.format(game_name, reaction))
        else:
            await ctx.send('Emoji must be a custom server emoji and must not be used by another game.')

@client.command()
@commands.has_any_role(game_master_id, club_officer_id)
async def edit_game_description(ctx, game_name_w_dashes : str, *, description):
    author_id = ctx.author.id
    is_club_officer = await check_if_club_officer(author_id)

    data = await open_json('sign_up_sheet.json')
    game_name = game_name_w_dashes.replace('-', ' ')

    if game_name not in data:
        await ctx.send('{} is not an existing game. If the game exists on the server but not in the sign up sheet you may use .add_game_data to add the game data to the sheet.'.format(game_name))
    elif author_id != data[game_name]['dm_id'] and not is_club_officer:
        await ctx.send('Sorry, you can not manage a game for another game master unless you are a club officer.')
    else:
        is_valid_description = await check_valid_description(description)
        if is_valid_description:
            message = 'Edit Game Description Request\nGame Name: {}\nNew Description:{}'.format(game_name, description)
            approved = await officer_approve(ctx, message)
            if approved:
                data[game_name]['description'] = description
                await write_json(data, 'sign_up_sheet.json')
                await update_sus()
                await ctx.send('The descripton for {} is {}'.format(game_name, description))
            else:
                guild = client.get_guild(guild_id)
                game_master = guild.get_member(data[game_name]['dm_id'])
                await ctx.send('{} Your edit request has been denied, an officer will message you explaining why and how to resolve the issue.'.format(game_master.mention))
        else:
            await ctx.send('Description must be less than 100 characters.')


#Sign up sheet commands for Club Officers
@client.command()
@commands.has_any_role(club_officer_id)
async def force_sus_update(ctx):
    await update_sus()

@client.command()
@commands.has_any_role(club_officer_id)
async def add_game_data(ctx, game_name, on_sus, max_players, reaction, game_master : discord.Member, role : discord.Role,category_id : int, *, description):
    '''Adds a new game to the sign up sheet file but does not make any changes to the discord
    name: str, the name of the game as it will be written in channels (with dashes), dashes will be replaced with spaces for sus
    on_sus: bool True if the game is listed on the sign up sheet, False if not
    max_players: int, max_number of players that can sign up for the game
    description: str, game description which should show on the sign up sheet
    reaction: str, emoji id, must be a emoji custom to the server, emoji used for reaction add
    role: the role of the game
    game_master: str, @user, game master of the game'''
    is_valid_name = await check_valid_game_name(game_name)
    is_valid_description = await check_valid_description(description)
    is_valid_emoji = await check_valid_emoji(reaction)

    if not is_valid_name:
        await ctx.send('Game name must be less than 45 characters and not have the same name as another game in the club.')
    elif not is_valid_description:
        await ctx.send('Description must be less than 100 characters.')
    elif not is_valid_emoji:
        await ctx.send('Emoji must be a custom server emoji and must not be used by another game.')
    else:
        name_w_spaces = game_name.replace('-', ' ')

        #Adds new game to sign_up_sheet.json
        data = await open_json('sign_up_sheet.json')
        game_data = {'on_sus': on_sus,
                'dm_id': game_master.id,
                'max_players': int(max_players),
                'role_id': role.id,
                'category': category_id,
                'description': description,
                'reaction': reaction,
                'player_ids': []}
        data[name_w_spaces] = game_data

        await write_json(data, 'sign_up_sheet.json')

        #update the sign up sheet message
        await update_sus()

        await ctx.send('Game data for {} has been added'.format(name_w_spaces))

@client.command()
@commands.has_any_role(club_officer_id)
async def remove_game_data(ctx, game_name_w_dashes):
    '''Removes a game from the sign up sheet file but does not make any changes to the discrod
    name: str, the name of the game as it will be written in channels (with dashes)'''

    data = await open_json('sign_up_sheet.json')

    game_name = game_name_w_dashes.replace('-', ' ')

    if ctx.channel.id != officer_bot_channel_id:
        await ctx.send('Please use the remove_game command in the #officer-bot-command text channel')
    elif game_name not in data:
        await ctx.send('{} is not an existing game. If the game exists on the server but not in the sign up sheet you may use .add_game_data to add the game data to the sheet.'.format(game_name))
    else:
        del data[game_name]
        await write_json(data, 'sign_up_sheet.json')
        await update_sus()
        await ctx.send('Game data for {} has been removed'.format(game_name))

@client.command()
@commands.has_any_role(club_officer_id)
async def add_player_data(ctx, game_name_w_dashes, member : discord.Member):
    '''Command for officers to manually add players to game data, but not change their roles
    member: str; @user, the player being added to the game
    game_name: str, the name of the game with dashes'''
    data = await open_json('sign_up_sheet.json')
    game_name = game_name_w_dashes.replace('-', ' ')
    if game_name not in data:
        await ctx.send('{} is not a game in the sign up sheet. If the game is not on the signup sheet add it first'.format(game_name))
    else:
        game_data = data[game_name]
        if member.id in game_data['player_ids']:
            await ctx.send('{} is already in this game, if they do not have the corret role manually give them the role.'.format(member.mention))
        else:
            #add player id to the game file
            data[game_name]['player_ids'].append(member.id)
            await write_json(data, 'sign_up_sheet.json')

            #update the sign up sheet message
            await update_sus()

            await ctx.send('{} has been added to the game data for {}'.format(member.mention, game_name))

@client.command()
@commands.has_any_role(club_officer_id)
async def remove_player_data(ctx, game_name_w_dashes, member : discord.Member):
    '''Command for officers to manually remove players from game data, but not change their roles
    member: str; @user, the player being added to the game
    game_name: str, the name of the game with dashes'''
    data = await open_json('sign_up_sheet.json')
    game_name = game_name_w_dashes.replace('-', ' ')
    if game_name not in data:
        await ctx.send('{} is not a game in the sign up sheet. If the game is not on the signup sheet add it first'.format(game_name))
    else:
        game_data = data[game_name]
        if member.id not in game_data['player_ids']:
            await ctx.send('{} is not in this game, if they mistakenly have the role manually remove it.'.format(member.mention))
        else:
            #remove player id from the game file
            data[game_name]['player_ids'].remove(member.id)
            await write_json(data, 'sign_up_sheet.json')

            #update the sign up sheet message
            await update_sus()

            await ctx.send('{} has been added to the game data for {}'.format(member.mention, game_name))

@client.event
async def on_member_join(user):
    guild = client.get_guild(guild_id)
    new_member_role = guild.get_role(new_member_role_id)

    await guild.get_member(user.id).add_roles(new_member_role)
    await user.send("Welcome to RPG at UCSB! To be able to access to the rest of the server, make sure to post in the #introductions channel of the server, following the format in #welcome")

@client.event
async def on_message(message):
    introductions_channel = await client.fetch_channel(introductions_channel_id)

    if message.channel == introductions_channel:
        guild = client.get_guild(guild_id)
        club_member_role = guild.get_role(club_member_role_id)
        club_officer_role = guild.get_role(club_officer_id)
        new_member_role = guild.get_role(new_member_role_id)
        club_user = message.author
        club_member = guild.get_member(club_user.id)

        current_time = time()
        end_time = current_time + 86400 

        while current_time < end_time: #will watch the message for a day (so officers have a day to react to the message and welcome the new club member)
            use_message = await message.channel.fetch_message(message.id)
            for i in range(len(use_message.reactions)):
                for user in use_message.reactions[i].users(): #for every user reacting to the message
                    if club_officer_role in guild.get_member(user.id).roles: #if a club officer is reacting
                        await club_member.add_roles(club_member_role)
                        await club_member.remove_role(new_member_role)
                        await club_user.send("Thank's for introducing yourself in RPG at UCSB! You now have access to the rest of the server, including the #sign-up-sheet where you can find games that are looking for players.")
                        break

@client.event
async def on_member_remove(user):
    channel = client.get_channel(officer_bot_channel_id)
    await channel.send('Oh no! Looks like {} has left the server :('.format(user))

@client.event
async def on_ready():
    bot_description = discord.Game('Just Swimming | .help')
    await client.change_presence(activity = bot_description)
    print('We have logged in as {0.user}'.format(client))

    #####SIGN UP SHEET MANAGEMENT####
    #get reactions and names of all games in sign up sheet doc
    open_games = await get_open_games()
    open_game_reactions = await get_open_game_reactions(open_games)


    #find initial reacting users
    previous_reacting_users = await find_reacting_users(sus_channel_id, sus_message_id, open_game_reactions)

    for i in range(1000000000):
        ####This section is for the sign up sheet####
        #pull updated data
        data = await open_json('sign_up_sheet.json')

        #find current reacting users
        current_reacting_users = await find_reacting_users(sus_channel_id, sus_message_id, open_game_reactions)

        #compare previous and current reacting users to find players added and players dropped
        players_added = await reactions_added(previous_reacting_users, current_reacting_users)
        players_dropped = await reactions_removed(previous_reacting_users, current_reacting_users)

        for game_name in players_added: #for each game that got new players
            for user_id in players_added[game_name]: #for each player added to the game
                game_data = data[game_name]
                if user_id in game_data['player_ids']:
                    await client.get_user(user_id).send('You are allready a player in {}, and can not sign up for it again.\nIf you would like to remove yourself from the game, you may remove the reaction you just made.'.format(game_name))
                elif user_id == game_data['dm_id']:
                    await client.get_user(user_id).send('You are the GM of {} and can not sign up for it. If you are geting this message in error, please contact a club officer.'.format(game_name))
                else:
                    await add_to_game(user_id, game_name)

        for game_name in players_dropped: #for each game that lost players
            for user_id in players_dropped[game_name]: #for each player removed from game
                game_data = data[game_name]
                if user_id == game_data['dm_id']: #if user is the game master
                    await client.get_user(user_id).send('You are the Game Master for {}, and therefore cannot remove yourself from it. If you would like to end your game or remove it from the sign up sheet, please use the end/edit game commands or message a club officer.'.format(game_name))
                elif user_id not in game_data['player_ids']: #if user is not in the game they are trying to remove themselves from
                    await client.get_user(user_id).send('You are not currently signed up for {}, so you can not remove yourself from the sign up sheet.\nIf you beleve you received this message in error, please message a club officer.'.format(game_name))
                else:
                    await remove_from_game(user_id, game_name)

        #update previous_reacting_users changed
        previous_reacting_users = current_reacting_users

        #get reactions and names of all games in sign up sheet doc
        open_games = await get_open_games()
        open_game_reactions = await get_open_game_reactions(open_games)

        ####This section is for event reminders####
        #event_date_list = []
        #event_name_list = []
        #data = await open_json('Bot_Info.json')
        #for json_event in data['event']:
        #    event_date_list.append(json_event["date"])
        #    event_name_list.append(json_event["event-name"])
        #officer_channel = client.get_channel(officer_channel_id)
        #datetime_now = datetime.datetime.now(pytz.timezone('US/Pacific')).replace(tzinfo = None)
        #name_index = 0
        #for date_string in event_date_list:
        #    try:
        #        date = datetime.datetime.strptime(date_string, '%m-%d-%Y %I:%M%p')
        #    except:
        #        date = datetime.datetime.strptime(date_string, '%m/%d/%Y %I:%M%p')
        #    if datetime_now > date:
        #        embed = discord.Embed(title = f'EVENT REMINDER', description = f'This reminder is for **{event_name_list[name_index]}**', 
        #            colour = 0Xfdbf32)
        #        embed.set_footer(text = f'Timestamp - {datetime.datetime.now()}')
        #        await officer_channel.send(embed = embed)
        #        data["event"].pop(name_index)
        #        await write_json(data, 'Bot_Info.json')
        #        break
        #    name_index = name_index + 1

        await asyncio.sleep(10)

client.run(token)