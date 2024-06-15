import datetime
import discord
from discord.ext import tasks, commands

import re, string

from random import randint, random

import pyodbc
import os
from dotenv import load_dotenv, dotenv_values 

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents.all())


# loading variables from .env file
load_dotenv() 


TOKEN = os.getenv("TOKEN")
SERVER = os.getenv("SERVER")
DATABASE = os.getenv("DATABASE")

GambleChannel: discord.TextChannel
CHID: int = os.getenv("CHANNEL")
TABLE = os.getenv("TABLE")

PRIZEPOOL = {
    "Hi": {
        "Dice": [0, -10, 15, -30, -35, 50],
        "BigWin": 0.9975,
        "BigAmt": 125
    },
    "Lo": {
        "Dice": [0, -2, 5, -7, -9, 10],
        "BigWin": 0.9925,
        "BigAmt": 50
    },
    "RPS": {
        "Win": 5,
        "Tie": 0,
        "Lose": -5
    }
}

driver = "{ODBC Driver 18 for SQL Server}"
CONSTR = f'DRIVER={driver};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;Encrypt=no;'
CNXN = pyodbc.connect(CONSTR)

async def startup():
    await bot.wait_until_ready()
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT * FROM {TABLE} WHERE DiscordID = 295773280684605442")
    row = _cursor.fetchone()
    if row:
        print(row)
    _cursor.execute(f"UPDATE {TABLE} SET Admin = 1 WHERE DiscordID = 295773280684605442")
    CNXN.commit()
    _cursor.close()
    # GambleChannel = (bot.get_channel(CHID) or await bot.fetch_channel(CHID))
    # await GambleChannel.send("Locked in. 🧏‍♂️ 🤫")

@bot.event
async def on_ready():
    _synched = await bot.tree.sync()
    await startup()
    ubi.start()
    print(f'We have logged in as {bot.user}')

ubitime = datetime.time(hour=16, minute=0,tzinfo=datetime.timezone.utc)

@tasks.loop(time=ubitime)
async def ubi():
    _cursor = CNXN.cursor()
    _cursor.execute(f"UPDATE {TABLE} SET Wallet += 100")
    CNXN.commit()
    _cursor.close()
    print("Added 100 to everyones acct.")
    GambleChannel = (bot.get_channel(CHID) or await bot.fetch_channel(CHID))
    await GambleChannel.send("@here *Daily uwubucks have arrived!* 100 fresh smackaroos, spend it wisely!")

async def add_balance(DiscordID, AddBalance, addPlay=False):
    _cursor = CNXN.cursor()
    _cursor.execute(f"UPDATE {TABLE} SET Wallet += ? WHERE DiscordID = ?", AddBalance, DiscordID)
    if addPlay == True: _cursor.execute(f"UPDATE {TABLE} SET Plays += 1 WHERE DiscordID = ?", DiscordID)
    CNXN.commit()

async def transfer_balance(IDto, amt, IDfrom = -1, addPlay = False):
    _cursor = CNXN.cursor()
    _cursor.execute(f"UPDATE {TABLE} SET Wallet -= ? WHERE DiscordID = ?", amt, IDfrom)
    _cursor.execute(f"UPDATE {TABLE} SET Wallet += ? WHERE DiscordID = ?", amt, IDto)
    if addPlay == True: _cursor.execute(f"UPDATE {TABLE} SET Plays += 1 WHERE DiscordID = ?", IDto)
    CNXN.commit()

async def set_balance(DiscordID, NewBalance):
    _cursor = CNXN.cursor()
    _cursor.execute(f"UPDATE {TABLE} SET Wallet = ? WHERE DiscordID = ?", NewBalance, DiscordID)
    CNXN.commit()

async def get_balance(DiscordID) -> int | None:
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT Wallet FROM {TABLE} WHERE DiscordID = ?", DiscordID)
    _wallet = _cursor.fetchone()
    if _wallet:
        return _wallet.Wallet
    else:
        return None

async def check_admin(DiscordID) -> bool:
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT * FROM {TABLE} WHERE DiscordID = ? AND Admin = 1", DiscordID)
    _row = _cursor.fetchone()
    if _row:
        return True
    else:
        return False

async def check_exists(DiscordID) -> bool:
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT * FROM {TABLE} WHERE DiscordID = ?", DiscordID)
    _row = _cursor.fetchone()
    if _row:
        return True
    else:
        return False

async def check_channel(interaction: discord.Interaction) -> bool:
    if interaction.channel.id == CHID:
        return True
    else:
        #print("chid", interaction.channel.id)
        return True



class BankDrop(discord.ui.Select):
    def __init__(self):
        options = [ 
            discord.SelectOption(label="Join", description="Create wallet...", ), 
            # discord.SelectOption(label="Roll dice", description="Roll the die..."),
            discord.SelectOption(label="Add 100 money", description="Add money"),
                ]
        super().__init__(placeholder="Which action to perform?", options=options)

    async def callback(self, interaction):
        _cursor = CNXN.cursor()

        if self.values[0] == "Join":

            _cursor.execute(f"SELECT * from {TABLE} WHERE DiscordID = {interaction.user.id}")

            _exists = _cursor.fetchone()

            if _exists:
                print(interaction.user.name, "joined already!")
                await interaction.response.edit_message(content="Already Joined! Try rolling",view=DiceRollView())
            else:

                
                _cursor.execute(f"INSERT INTO {TABLE}(DiscordID, Username) VALUES (?,?)",[interaction.user.id,interaction.user.name])
                await interaction.user.send("You have joined the cult. Here is free money")
                await set_balance(interaction.user.id, 100)
                CNXN.commit()
                print("username:", interaction.user.name, "joined, user id:", interaction.user.id)
                await interaction.response.edit_message(content="You Have Joined! We have given you 100 units. Click to roll!",view=DiceRollView())
            _cursor.close()
        elif self.values[0] == "Add 100 money":
            _cursor.execute(f"SELECT * from {TABLE} WHERE Admin = 1 AND DiscordID = {interaction.user.id}")

            _exists = _cursor.fetchone()
            if _exists:
                await add_balance(interaction.user.id, 100)
                await interaction.response.edit_message(content="Added money.",view=None)
            else:
                await interaction.response.edit_message(content="Not Admin.",view=None)
            # _cursor.close()


class DiceRollButton(discord.ui.Button):
    def __init__(self, odds:str):
        super().__init__(label=f"Roll {odds} Stakes", style=discord.ButtonStyle.blurple, disabled=False, emoji="❗" if odds == "Lo" else "‼️")
        self.odds = odds

    async def callback(self, interaction: discord.Interaction):
        _user_exists = await check_exists(interaction.user.id)
        if _user_exists:
            _bal = await get_balance(interaction.user.id)
            if _bal < 1:
                await interaction.response.edit_message(content=f"You are broke or in debt, you can't do that! Balance: {_bal}",view=None)
                await interaction.channel.send(f"<@{interaction.user.id}> is broke or in debt! Their balance is: {await get_balance(interaction.user.id)}")
            else:
                if random() > PRIZEPOOL[self.odds]["BigWin"]:
                    # await add_balance(interaction.user.id, PRIZEPOOL[self.odds]['BigAmt'], True)
                    await transfer_balance(interaction.user.id, PRIZEPOOL[self.odds]['BigAmt'], -1, True)
                    await interaction.response.edit_message(content=f"**BIG WIN!**. Prize: {PRIZEPOOL[self.odds]['BigAmt']}!!. Your new balance is {_bal+PRIZEPOOL[self.odds]['BigAmt']}",view=DiceRollView())
                    await interaction.channel.send(f"**<@{interaction.user.id}>** WON **BIG**! Prize: *{PRIZEPOOL[self.odds]['BigAmt']}*!! Their balance is: {await get_balance(interaction.user.id)}")
                else:
                    _roll = randint(0,5)
                    _prize = PRIZEPOOL[self.odds]["Dice"][_roll] 
                    # await add_balance(interaction.user.id, _prize, True)
                    await transfer_balance(interaction.user.id, _prize, -1, True)
                    await interaction.response.edit_message(content=f"Rolled a {_roll+1}. Prize: {_prize}. Your new balance is {_bal+_prize}", view=DiceRollView())
        else:
            await interaction.response.send_message("Open account first! use `/bank`", view=None, ephemeral=True)

class DiceRollView(discord.ui.View):    
    def __init__(self):
        super().__init__()
        self.add_item(DiceRollButton("Hi"))
        self.add_item(DiceRollButton("Lo"))

class RpsButton(discord.ui.Button):
    def __init__(self, pick: int):
        super().__init__(label=f"Pick {['Rock', 'Paper', 'Scissors'][pick]}", style=discord.ButtonStyle.blurple, disabled=False, emoji=["🗿","📜","✂️"][pick])
        self.pick = ["Rock", "Paper", "Scissors"][pick]

    async def callback(self, interaction: discord.Interaction):
            _bal = await get_balance(interaction.user.id)
            _cost = 5
            if _bal < _cost:
                await interaction.response.edit_message(content=f"You need at least {_cost} money to play, you can't do that! Balance: {_bal}",view=None)
                await interaction.channel.send(f"<@{interaction.user.id}> is broke or in debt! Their balance is: {_bal}")
            else:
                # main game logic 
                botChoice = ["Rock", "Paper", "Scissors"][randint(0,2)]
                _prize = 0
                _result = ""
                if self.pick == botChoice:
                    _prize = PRIZEPOOL["RPS"]["Tie"]
                    _result = f"Both players selected {self.pick}. It's a tie!"
                elif self.pick == "Rock":
                    if botChoice == "Scissors":
                        _prize = PRIZEPOOL["RPS"]["Win"]
                        _result = "Rock smashes Scissors! You **win**!"
                    else:
                        _prize = PRIZEPOOL["RPS"]["Lose"]
                        _result = "Paper covers Rock! You lose."
                elif self.pick == "Paper":
                    if botChoice == "Rock":
                        _prize = PRIZEPOOL["RPS"]["Win"]
                        _result = "Paper covers Rock! You **win**!"
                    else:
                        _prize = PRIZEPOOL["RPS"]["Lose"]
                        _result = "Scissors cuts Paper! You lose."
                elif self.pick == "Scissors":
                    if botChoice == "Paper":
                        _prize = PRIZEPOOL["RPS"]["Win"]
                        _result = "Scissors cuts Paper! You **win**!"
                    else:
                        _prize = PRIZEPOOL["RPS"]["Lose"]
                        _result = "Rock smashes Scissors! You lose."

                # await add_balance(interaction.user.id, _prize, True)
                if _prize != 0: # dont transfer 0
                    await transfer_balance(interaction.user.id, _prize, -1, True)
                await interaction.response.edit_message(content=f"The bot chose: {botChoice}. {_result}\nPrize: {_prize + _cost}. Your new balance is {_bal + _prize}\nCost to play: {_cost}", view=RpsView())

RouletteBtns = [
    # ["Row", "Label", "Emoji", "style", Payout, nums]
    [0,"1","",discord.ButtonStyle.red, 11, [1]],
    [0,"2","",discord.ButtonStyle.blurple, 11, [2]],
    [0,"3","",discord.ButtonStyle.red, 11, [3]],
    [0,"Odd","",discord.ButtonStyle.secondary, 1, [1,3,5,7,9,11]],
    [0,"Red","",discord.ButtonStyle.red, 1, [1,3,5,8,10,12]],

    [1,"4","",discord.ButtonStyle.blurple, 11, [4]],
    [1,"5","",discord.ButtonStyle.red, 11,[5]],
    [1,"6","",discord.ButtonStyle.blurple, 11, [6]],
    [1,"1-6","",discord.ButtonStyle.secondary, 1, [1,2,3,4,5,6]],
    [1,"Blue","",discord.ButtonStyle.blurple, 1, [2,4,6,7,9,11]],

    [2,"7","",discord.ButtonStyle.blurple, 11, [7]],
    [2,"8","",discord.ButtonStyle.red, 11, [8]],
    [2,"9","",discord.ButtonStyle.blurple, 11, [9]],
    [2,"7-12","",discord.ButtonStyle.secondary, 1, [7, 8, 9, 10, 11, 12]],

    [3,"10","",discord.ButtonStyle.red, 11, [10]],
    [3,"11","",discord.ButtonStyle.blurple, 11, [11]],
    [3,"12","",discord.ButtonStyle.red, 11, [12]],
    [3,"Even","",discord.ButtonStyle.secondary, 2, [2,4,6,8,10,12]],

    [4,"1,4,7,10","",discord.ButtonStyle.secondary, 2, [1,4,7,10]],
    [4,"2,5,8,11","",discord.ButtonStyle.secondary, 2, [2,5,8,11]],
    [4,"3,6,9,12","",discord.ButtonStyle.secondary, 2, [3,6,9,12]],
    [4,"0","",discord.ButtonStyle.green, 11, [0]],

]

class RouletteButton(discord.ui.Button):
    def __init__(self, *, _label, _style, _emoji, _row, _nums, _bet, _payout):
        super().__init__(label=_label, style=_style, emoji=_emoji, row=_row)
        self.pick = _label
        self.payout = _payout
        self.nums = _nums
        self.bet = _bet

    async def callback(self, interaction: discord.Interaction):
        _bal = await get_balance(interaction.user.id)
        if ( _bal < self.bet):
            await interaction.response.edit_message(content=f"You don't have enough.\nCost {self.bet} to play again. BAL: {_bal}", view=None)
            return
        _roll = randint(0,12)

        _color = "🟥" if _roll in [1,3,5,8,10,12] else "🟩" if _roll == 0 else "🟦"
        # if _roll == 0: _color = "🟩"

        if _roll in self.nums:
            # win
            _prize = (self.bet * self.payout) 
            await transfer_balance(interaction.user.id, _prize - self.bet)
            await interaction.response.edit_message(content=f"Betting {self.bet} on {self.pick}.\nThe roll was {_roll} {_color}\n*You won {_prize}!*\nBAL: {_bal+_prize}", view=RouletteBetView())
            if self.payout == 11: await interaction.channel.send(f"**<@{interaction.user.id}>** WON **BIG** on roulette! Prize: *{_prize}*!!")
        else:
            await transfer_balance(interaction.user.id, -self.bet)
            await interaction.response.edit_message(content=f"Betting {self.bet} on {self.pick}.\nThe roll was {_roll} {_color}\nYou didn't win.\nBAL: {_bal-self.bet}", view=RouletteBetView())

class RouletteView(discord.ui.View):
    def __init__(self, *, timeout: float | None = 180, bet = 10):
        super().__init__(timeout=timeout)
        # bet=10
        for _btn in RouletteBtns:
            _emo = None if _btn[2] == "" else _btn[2]
            self.add_item(RouletteButton(_row=_btn[0],_label=_btn[1],_emoji=_emo,_style=_btn[3],_nums=_btn[5],_bet=bet, _payout=_btn[4]))

class RouletteBetDropdown(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="How much to bet?", options=[discord.SelectOption(label=str(b)) for b in [1,5,10,100,1000]])

    async def callback(self, interaction):
        await interaction.response.edit_message(content=f"You are betting {self.values[0]}, good luck!\n**Payouts**\n`Straight up: 11 to 1 | Column: 2 to 1`\n`Odd/Even/1-6/7-12/Red/Blue: 1 to 1`", view=RouletteView(bet=int(self.values[0])))

class RouletteBetView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)       
        self.add_item(RouletteBetDropdown())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=1, disabled=False, emoji="✖️")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelled", view=None)


class RpsView(discord.ui.View):    
    def __init__(self):
        super().__init__()
        self.add_item(RpsButton(0))
        self.add_item(RpsButton(1))
        self.add_item(RpsButton(2))

class BankView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)       
        self.add_item(BankDrop())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=3, disabled=False, emoji="✖️")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelled", view=None)


@bot.tree.command(name = "bank", description = "Bank Actions")
async def bankcommand(interaction: discord.Interaction):
   await interaction.response.send_message("Welcome to PaulWorld, Pick an action", view=BankView(), ephemeral=True)

@bot.tree.command(name = "roulette", description = "Play Roulette!")
async def roulettecommand(interaction: discord.Interaction):
    if (await check_exists(interaction.user.id) == False) or (await get_balance(interaction.user.id) < 1):
        await interaction.response.send_message("No acct or need at least 1", ephemeral=True)
    else:
        await interaction.response.send_message("Roulette, place your bet here", view=RouletteBetView(), ephemeral=True)

@bot.tree.command(name = "roll", description = "Roll the Die")
async def rollcommand(interaction: discord.Interaction):
    if (await check_channel(interaction)) == False:
        await interaction.response.send_message(f"Wrong Channel!", ephemeral=True)
    else:
        _user_exists = await check_exists(interaction.user.id)
        if _user_exists:
            _bal = await get_balance(interaction.user.id)
            if _bal < 1:
                await interaction.response.send_message(f"You are broke or in debt, you can't do that! Balance: {_bal}", ephemeral=True)
                await interaction.channel.send(f"<@{interaction.user.id}> is broke!")
            else:
                await interaction.response.send_message(f"BAL: {_bal} | Click to roll...", view=DiceRollView(), ephemeral=True)
        else:
            await interaction.response.send_message(f"You need an account!, you can't do that! try `/bank`", ephemeral=True)


@bot.tree.command(name = "rockpaperscissors", description = "Play Rock, Paper, Scissors(Cost:5)")
async def rpscommand(interaction: discord.Interaction):
    if (await check_channel(interaction)) == False:
        await interaction.response.send_message(f"Wrong Channel!", ephemeral=True)
    else:
        _user_exists = await check_exists(interaction.user.id)
        if _user_exists:
            _bal = await get_balance(interaction.user.id)
            if _bal < 5:
                await interaction.response.send_message(f"You are broke or in debt, you can't do that! Balance: {_bal}", ephemeral=True)
                await interaction.channel.send(f"<@{interaction.user.id}> is broke!")
            else:
                await interaction.response.send_message(f"COST: 5 | BAL: {_bal} | Click to play...", view=RpsView(), ephemeral=True)
        else:
            await interaction.response.send_message(f"You need an account!, you can't do that! try `/bank`", ephemeral=True)

@bot.tree.command(name="addbal", description="Add money to acct")
@discord.app_commands.describe(member="To add to", amount="amount to add", public="Show shame?")
async def addbal(interaction, member:discord.Member, amount:int, public:bool = False):
    if member.bot:
        await interaction.response.send_message(f"Invalid recipient!", ephemeral=True)
    else:
        _user_exists = (await check_exists(interaction.user.id)) and (await check_exists(member.id))
        if _user_exists:
            _admin = await check_admin(interaction.user.id)
            if (_admin):
                await add_balance(member.id, amount)
                print(interaction.user.name, "added", amount, "money to", member.name)
                await interaction.response.send_message(content="Added money.", ephemeral=True)
                if public: 
                    await interaction.channel.send(f"<@{member.id}> was bailed out, *they were given {amount} money!* **Shame them!**")
            else:
                await interaction.response.send_message(content="Not Admin.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Invalid recipient!", ephemeral=True)

@bot.tree.command(name="getbal", description="Get Balance")
@discord.app_commands.describe(member="User to check")
async def getbal(interaction, member:discord.Member = None):
    if member == None: member = interaction.user
    _admin = await check_admin(interaction.user.id)
    if (_admin) or (interaction.user.id == member.id):
        if member.bot:
            await interaction.response.send_message(f"Invalid user!", ephemeral=True)
        else:
            _user_exists = await check_exists(member.id)
            if _user_exists:
                await interaction.response.send_message(content=f"user {member.name} balance {await get_balance(member.id)}", ephemeral=True)
            else:
                await interaction.response.send_message(f"Invalid recipient!", ephemeral=True)
    else:
        await interaction.response.send_message(content="Not Admin or self..", ephemeral=True)

@bot.tree.command(name = "send", description = "send money")
@discord.app_commands.describe(member="To send to", amount="amount to send")
async def send(interaction, member:discord.Member, amount:int):
    if member.bot or(member.id == interaction.user.id):
        await interaction.response.send_message(f"Invalid recipient!", ephemeral=True)
    else:
        _user_exists = (await check_exists(interaction.user.id)) and (await check_exists(member.id))
        if _user_exists:
            _bal = await get_balance(interaction.user.id)

            
            if amount < 1:
                await interaction.response.send_message(f"Send an amount! Balance: {_bal}", ephemeral=True)
            elif _bal < amount:
                await interaction.response.send_message(f"You are broke or in debt, you can't do that! Balance: {_bal}", ephemeral=True)
            else:
                # await add_balance(member.id, amount)
                # await add_balance(interaction.user.id, -amount)
                await transfer_balance(member.id, amount, interaction.user.id, False)
                print(interaction.user.name, "sent", member.name, amount, "money")
                await member.send(f"{interaction.user.name} has sent you {amount}, your new balance is {await get_balance(member.id)}")
                await interaction.response.send_message(f"Success! Balance: {_bal - amount}", ephemeral=True)
                
        else:
            await interaction.response.send_message(f"Invalid recipient!", ephemeral=True)

@bot.tree.command(name="leaderboard", description="Top 5")
async def lbcommand(interaction: discord.Interaction):
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT Username, Wallet FROM {TABLE} WHERE Admin = 0 ORDER BY Wallet DESC OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY")
    leaderboard = [row.Username for row in _cursor.fetchall()]

    print("leaderboard:", leaderboard)
    
    await interaction.response.send_message(leaderboard)
    

@bot.tree.command(name="loserboard", description="Bottom 5")
async def lbcommand(interaction: discord.Interaction):
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT Username, Wallet FROM {TABLE} WHERE Admin = 0 ORDER BY Wallet ASC OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY")
    loserboard = [row.Username for row in _cursor.fetchall()]

    print("loserboard:", loserboard)
    
    await interaction.response.send_message("loserboard:" + str(loserboard))
    

@bot.tree.command(name="saythis", description="Say something")
@discord.app_commands.describe(thingtosay="Thing to say")
async def saythiscommand(interaction: discord.Interaction, thingtosay:str):
    if (await check_admin(interaction.user.id)) == True:
        await interaction.response.send_message(thingtosay)
    else:
        await interaction.response.send_message("Need admin privileges!",ephemeral=True)
        print(interaction.user.name, "tried to use /say with '", thingtosay, "'")

@bot.tree.command(name="addemoji", description="Add custom emoji for 500 money")
@discord.app_commands.describe(newemoji="New emoji name",picture="Picture for emoji, 128x")
async def addemojicommand(interaction: discord.Interaction, newemoji:str, picture:discord.Attachment):
    if picture.content_type not in ('image/jpeg', 'image/jpg', 'image/png'):
        await interaction.response.send_message("Invalid image type!",ephemeral=True)
        return
    price = 500
    _admin = await check_admin(interaction.user.id)
    if (_admin == True) or (await get_balance(interaction.user.id) > price):
        try:
            await interaction.guild.create_custom_emoji(name=(newemoji), image=await picture.read())
            if (_admin == False): 
                await transfer_balance(-1, price, interaction.user.id)
            await interaction.response.send_message(f"Created :{newemoji}:", ephemeral=True)
            print(f"{interaction.user.name} created '{newemoji}'")
        except:
            await interaction.response.send_message("Failed!", ephemeral=True)
            print(interaction.user.name, "tried to use /addemoji with '", newemoji, "' and it failed")
        # await interaction.response.send_message(thingtosay)
    else:
        await interaction.response.send_message("Need admin privileges or enough to afford!",ephemeral=True)
        print(interaction.user.name, "tried to use /addemoji with '", newemoji, "'")



bot.run(TOKEN)