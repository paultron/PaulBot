import datetime
import discord
from discord.ext import tasks, commands



from random import randint, random

import pyodbc
import os
from dotenv import load_dotenv, dotenv_values 

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


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
    # await GambleChannel.send("Locked in. 🤫")

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
    _cursor.execute(f"UPDATE {TABLE} SET Wallet = Wallet + 100")
    CNXN.commit()
    _cursor.close()
    print("Added 100 to everyones acct.")
    GambleChannel = (bot.get_channel(CHID) or await bot.fetch_channel(CHID))
    await GambleChannel.send("@here *Daily uwubucks have arrived!* 100 fresh smackaroos, spend it wisely!")

async def add_balance(DiscordID, AddBalance, addPlay=False):
    _cursor = CNXN.cursor()
    _cursor.execute(f"UPDATE {TABLE} SET Wallet += {AddBalance} WHERE DiscordID = {DiscordID}")
    if addPlay == True: _cursor.execute(f"UPDATE {TABLE} SET Plays += 1 WHERE DiscordID = {DiscordID}")
    CNXN.commit()

async def set_balance(DiscordID, NewBalance):
    _cursor = CNXN.cursor()
    _cursor.execute(f"UPDATE {TABLE} SET Wallet = {NewBalance} WHERE DiscordID = {DiscordID}")
    CNXN.commit()

async def get_balance(DiscordID) -> int | None:
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT Wallet FROM {TABLE} WHERE DiscordID = {DiscordID}")
    _wallet = _cursor.fetchone()
    if _wallet:
        return _wallet.Wallet
    else:
        return None

async def check_admin(DiscordID) -> bool:
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT * FROM {TABLE} WHERE DiscordID = {DiscordID} AND Admin = 1")
    _row = _cursor.fetchone()
    if _row:
        return True
    else:
        return False

async def check_exists(DiscordID) -> bool:
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT * FROM {TABLE} WHERE DiscordID = {DiscordID}")
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
        super().__init__(placeholder="Which action to perform?",options=options)

    async def callback(self, interaction):
        _cursor = CNXN.cursor()

        if self.values[0] == "Join":

            _cursor.execute(f"SELECT * from {TABLE} WHERE DiscordID = {interaction.user.id}")

            _exists = _cursor.fetchone()

            if _exists:
                print(interaction.user.name, "joined already!")
                await interaction.response.edit_message(content="Already Joined! Try rolling",view=DiceRollView())
            else:
                print("joined")
                print("user id:", interaction.user.id)
                print("username:", interaction.user.name)
                
                _cursor.execute(f"INSERT INTO {TABLE}(DiscordID, Username) VALUES (?,?)",[interaction.user.id,interaction.user.name])
                await interaction.user.send("You have joined the cult. Here is free money")
                await set_balance(interaction.user.id, 100)
                CNXN.commit()
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
                    await add_balance(interaction.user.id, PRIZEPOOL[self.odds]['BigAmt'], True)
                    await interaction.response.edit_message(content=f"**BIG WIN!**. Prize: {PRIZEPOOL[self.odds]['BigAmt']}!!. Your new balance is {_bal+PRIZEPOOL[self.odds]['BigAmt']}",view=DiceRollView())
                    await interaction.channel.send(f"**<@{interaction.user.id}>** WON **BIG**! Prize: *{PRIZEPOOL[self.odds]['BigAmt']}*!! Their balance is: {await get_balance(interaction.user.id)}")
                else:
                    _roll = randint(0,5)
                    _prize = PRIZEPOOL[self.odds]["Dice"][_roll] 
                    await add_balance(interaction.user.id, _prize, True)
                    
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
            if _bal < 5:
                await interaction.response.edit_message(content=f"You need at least 5 money to play, you can't do that! Balance: {_bal}",view=None)
                await interaction.channel.send(f"<@{interaction.user.id}> is broke or in debt! Their balance is: {await get_balance(interaction.user.id)}")
            else:
                # main game logic
                _cost = 5 
                botChoice = ["Rock", "Paper", "Scissors"][randint(0,2)]

                if self.pick == botChoice:
                    _prize = PRIZEPOOL["RPS"]["Tie"]
                    await add_balance(interaction.user.id, _prize, True)
                    await interaction.response.edit_message(content=f"Both players selected {self.pick}. It's a tie!. Prize: {_prize + _cost}. Your new balance is {_bal+_prize}", view=RpsView())
                    # print(f"Both players selected {self.pick}. It's a tie!")
                elif self.pick == "Rock":
                    if botChoice == "Scissors":
                        _prize = PRIZEPOOL["RPS"]["Win"]
                        await add_balance(interaction.user.id, _prize, True)
                        await interaction.response.edit_message(content=f"Rock smashes Scissors! You win!. Prize: {_prize + _cost}. Your new balance is {_bal+_prize}", view=RpsView())
                        # print("Rock smashes Scissors! You win!")
                    else:
                        _prize = PRIZEPOOL["RPS"]["Lose"]
                        await add_balance(interaction.user.id, _prize, True)
                        await interaction.response.edit_message(content=f"Paper covers Rock! You lose. Prize: {_prize + _cost}. Your new balance is {_bal+_prize}", view=RpsView())
                        # print("Paper covers Rock! You lose.")
                elif self.pick == "Paper":
                    if botChoice == "Rock":
                        _prize = PRIZEPOOL["RPS"]["Win"]
                        await add_balance(interaction.user.id, _prize, True)
                        await interaction.response.edit_message(content=f"Paper covers Rock! You win!. Prize: {_prize + _cost}. Your new balance is {_bal+_prize}", view=RpsView())
                        # print("Paper covers Rock! You win!")
                    else:
                        _prize = PRIZEPOOL["RPS"]["Lose"]
                        await add_balance(interaction.user.id, _prize, True)
                        await interaction.response.edit_message(content=f"Scissors cuts Paper! You lose. Prize: {_prize + _cost}. Your new balance is {_bal+_prize}", view=RpsView())
                        # print("Scissors cuts Paper! You lose.")
                elif self.pick == "Scissors":
                    if botChoice == "Paper":
                        _prize = PRIZEPOOL["RPS"]["Win"]
                        await add_balance(interaction.user.id, _prize, True)
                        await interaction.response.edit_message(content=f"Scissors cuts Paper! You win!. Prize: {_prize + _cost}. Your new balance is {_bal+_prize}", view=RpsView())
                        # print("Scissors cuts Paper! You win!")
                    else:
                        _prize = PRIZEPOOL["RPS"]["Lose"]
                        await add_balance(interaction.user.id, _prize, True)
                        await interaction.response.edit_message(content=f"Rock smashes Scissors! You lose. Prize: {_prize + _cost}. Your new balance is {_bal+_prize}", view=RpsView())
                        # print("Rock smashes Scissors! You lose.")


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
    if member.bot:
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
                await add_balance(member.id, amount)
                await add_balance(interaction.user.id, -amount)
                print(interaction.user.name, "sent", member.name, amount, "money")
                await member.send(f"{interaction.user.name} has sent you {amount}, your new balance is {await get_balance(member.id)}")
                await interaction.response.send_message(f"Success! Balance: {_bal - amount}", ephemeral=True)
                
        else:
            await interaction.response.send_message(f"Invalid recipient!", ephemeral=True)

@bot.tree.command(name="leaderboard", description="Top 5")
async def lbcommand(interaction: discord.Interaction):
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT Username, Wallet from {TABLE} ORDER BY Wallet DESC OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY")
    leaderboard = [row.Username for row in _cursor.fetchall()]

    print("leaderboard:", leaderboard)
    
    await interaction.response.send_message(leaderboard)
    

@bot.tree.command(name="loserboard", description="Bottom 5")
async def lbcommand(interaction: discord.Interaction):
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT Username, Wallet from {TABLE} ORDER BY Wallet ASC OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY")
    loserboard = [row.Username for row in _cursor.fetchall()]

    print("loserboard:", loserboard)
    
    await interaction.response.send_message("loserboard:" + str(loserboard))
    

bot.run(TOKEN)