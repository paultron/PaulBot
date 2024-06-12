import discord
from discord.ext import commands

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
TABLE ="dbo.TestUsers"

PRIZEPOOL = {
    "Dice01": [0, 15, -15, -30, -35, 50],
    "BigWin": 0.995,
    "BigAmt": 125
}

driver = "{ODBC Driver 18 for SQL Server}"

CONSTR = f'DRIVER={driver};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;Encrypt=no;'

CNXN = pyodbc.connect(CONSTR)
# cursor = CNXN.cursor()


def connectServer() -> pyodbc.Connection:
    # _cnx = pyodbc.connect(CONSTR)
    print(f"connected to {DATABASE}")
    # return _cnx

async def startup() -> None:
    await bot.wait_until_ready()
    GambleChannel = (bot.get_channel(CHID) or await bot.fetch_channel(CHID))
    await GambleChannel.send("Logged in.")

@bot.event
async def on_ready():
    _synched = await bot.tree.sync()
    # CNXN = connectServer()
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT * FROM {TABLE} WHERE DiscordID = 295773280684605442")
    row = _cursor.fetchone()
    if row:
        print(row)
    _cursor.execute(f"UPDATE {TABLE} SET Admin = 1 WHERE DiscordID = 295773280684605442")
    CNXN.commit()
    _cursor.close()
    await startup()
    print(f'We have logged in as {bot.user}')

async def add_balance(DiscordID, AddBalance):
    _cursor = CNXN.cursor()
    _cursor.execute(f"UPDATE {TABLE} SET Wallet += {AddBalance} WHERE DiscordID = {DiscordID}")
    CNXN.commit()

async def set_balance(DiscordID, NewBalance):
    _cursor = CNXN.cursor()
    _cursor.execute(f"UPDATE {TABLE} SET Wallet = {NewBalance} WHERE DiscordID = {DiscordID}")
    CNXN.commit()

async def get_balance(DiscordID) -> int:
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
            
class DiceRollView(discord.ui.View):    
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Roll", style=discord.ButtonStyle.blurple, disabled=False, emoji="🎲")
    async def callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        _user_exists = await check_exists(interaction.user.id)
        if _user_exists:
            _bal = await get_balance(interaction.user.id)
            if _bal < 1:
                await interaction.response.edit_message(content=f"You are broke or in debt, you can't do that! Balance: {_bal}",view=None)
                await interaction.channel.send(f"<@{interaction.user.id}> is broke or in debt! Their balance is: {await get_balance(interaction.user.id)}")
            else:

                if random() > PRIZEPOOL["BigWin"]:
                    await add_balance(interaction.user.id, PRIZEPOOL['BigAmt'])
                    await interaction.response.edit_message(content=f"**BIG WIN!**. Prize: {PRIZEPOOL['BigAmt']}!!. Your new balance is {_bal+PRIZEPOOL['BigAmt']}",view=DiceRollView())
                    await interaction.channel.send(f"**<@{interaction.user.id}>** WON **BIG**! Prize: *{PRIZEPOOL['BigAmt']}*!! Their balance is: {await get_balance(interaction.user.id)}")
                else:
                    _roll = randint(0,5)
                    _prize = PRIZEPOOL["Dice01"][_roll] 
                    await add_balance(interaction.user.id, _prize)
                    
                    await interaction.response.edit_message(content=f"Rolled a {_roll+1}. Prize: {_prize}. Your new balance is {_bal+_prize}", view=DiceRollView())
        else:
            await interaction.response.send_message("Open account first! use `/bank`", view=None, ephemeral=True)


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

@bot.tree.command(name="addbal", description="Add money to acct")
@discord.app_commands.describe(member="To send to", amount="amount to add", public="Show shame?")
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
                await interaction.channel.send(f"<@{member.id}> was bailed out, *they were given {amount} money!* **Shame them!**")
            else:
                await interaction.response.send_message(content="Not Admin.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Invalid recipient!", ephemeral=True)

@bot.tree.command(name="getbal", description="Get Balance")
@discord.app_commands.describe(member="User to check")
async def addbal(interaction, member:discord.Member):
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

bot.run(TOKEN)