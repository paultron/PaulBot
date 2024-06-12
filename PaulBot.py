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

TABLE ="dbo.TestUsers"

PRIZEPOOL = {
    "Dice01": [0,15,-15,-30,-40,70],
}

driver = "{ODBC Driver 18 for SQL Server}"

CONSTR = f'DRIVER={driver};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;Encrypt=no;'

CNXN = pyodbc.connect(CONSTR)
# cursor = CNXN.cursor()


def connectServer() -> pyodbc.Connection:
    # _cnx = pyodbc.connect(CONSTR)
    print(f"connected to {DATABASE}")
    # return _cnx

@bot.event
async def on_ready():
    _synched = await bot.tree.sync()
    # CNXN = connectServer()
    _cursor = CNXN.cursor()

    _cursor.execute(f"SELECT * FROM {TABLE}")

    row = _cursor.fetchone()

    if row:
        print(row)
    _cursor.execute(f"UPDATE {TABLE} SET Admin = 1 WHERE DiscordID = 295773280684605442")
    CNXN.commit()
    _cursor.close()
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

async def check_exists(DiscordID) -> bool:
    _cursor = CNXN.cursor()
    _cursor.execute(f"SELECT * FROM {TABLE} WHERE DiscordID = {DiscordID}")
    _row = _cursor.fetchone()
    if _row:
        return True
    else:
        return False

class BankDrop(discord.ui.Select):
    def __init__(self):

        options = [ 
            discord.SelectOption(label="Join", description="Add info to db...", ), 
            # discord.SelectOption(label="Roll dice", description="Roll the die..."),
            discord.SelectOption(label="Add 100p", description="Add p"),
                ]
        super().__init__(placeholder="Which action to perform?",options=options)

    async def callback(self, interaction):
        _cursor = CNXN.cursor()

        if self.values[0] == "Join":

            _cursor.execute(f"SELECT * from {TABLE} WHERE DiscordID = {interaction.user.id}")

            _exists = _cursor.fetchone()

            if _exists:
                print("joined already!")
                await interaction.response.edit_message(content="Already Joined!",view=None)
            else:
                print("joined")
                print("user id:", interaction.user.id)
                print("username:", interaction.user.name)
                
                _cursor.execute(f"INSERT INTO {TABLE}(DiscordID, Username) VALUES (?,?)",[interaction.user.id,interaction.user.name])
                await interaction.user.send("You have joined the cult. Here is free money")
                await set_balance(interaction.user.id, 100)
                CNXN.commit()
                await interaction.response.edit_message(content="You Have Joined!",view=None)
            _cursor.close()
        elif self.values[0] == "Add 100p":
            _cursor.execute(f"SELECT * from {TABLE} WHERE Admin = 1 AND DiscordID = {interaction.user.id}")

            _exists = _cursor.fetchone()
            if _exists:
                await add_balance(interaction.user.id, 100)
                await interaction.response.edit_message(content="Added money.",view=None)
            else:
                await interaction.response.edit_message(content="Not Admin.",view=None)
            # _cursor.close()
            

class DiceRollButton(discord.ui.Button):
    def __init__(self):
        super().__init__()
        # self.value = None

    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.blurple, disabled=False, emoji="✖️")
    async def callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        _roll = randint(0,5)
        _prize = PRIZEPOOL["Dice01"][_roll]
        _bal = await get_balance(interaction.user.id)
        if _bal < 1:
            await interaction.response.edit_message(content=f"You are broke or in debt, you can't do that! Balance: {_bal}",view=None)
        else:
            await add_balance(interaction.user.id, _prize)
            
            await interaction.response.edit_message(content=f"Rolled a {_roll+1}. Prize: {_prize}. Your new balance is {_bal+_prize}",view=None)


        await interaction.response.edit_message(content="Cancelled", view=None)

class DiceRollView(discord.ui.View):

    rollBtn: DiceRollButton
    
    def __init__(self):
        super().__init__()
        self.value = None
        # self.add_item(DiceRollButton())

    @discord.ui.button(label="Roll", style=discord.ButtonStyle.blurple, row=3, disabled=False, emoji="🎲")
    async def roll_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        _user_exists = await check_exists(interaction.user.id)
        if _user_exists:
            _bal = await get_balance(interaction.user.id)
            if _bal < 1:
                await interaction.response.edit_message(content=f"You are broke or in debt, you can't do that! Balance: {_bal}",view=None)
                await interaction.channel.send(f"<@{interaction.user.id}> is broke or in debt! Their balance is: {await get_balance(interaction.user.id)}")
            else:

                if random() >0.98:
                    await add_balance(interaction.user.id, 150)
                    await interaction.response.edit_message(content=f"**BIG WIN!**. Prize: 150!!. Your new balance is {_bal+150}",view=DiceRollView())
                    await interaction.channel.send(f"**<@{interaction.user.id}> WON BIG**! Prize: 150!! Their balance is: {await get_balance(interaction.user.id)}")
                else:
                    _roll = randint(0,5)
                    _prize = PRIZEPOOL["Dice01"][_roll] 
                    await add_balance(interaction.user.id, _prize)
                    
                    await interaction.response.edit_message(content=f"Rolled a {_roll+1}. Prize: {_prize}. Your new balance is {_bal+_prize}",view=DiceRollView())
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
    _user_exists = await check_exists(interaction.user.id)
    if _user_exists:
        _bal = await get_balance(interaction.user.id)
        if _bal < 1:
            await interaction.response.send_message(f"You are broke or in debt, you can't do that! Balance: {_bal}")
            await interaction.channel.send(f"<@{interaction.user.id}> is broke!")
        else:
            await interaction.response.send_message(f"BAL: {_bal} | Click to roll...", view=DiceRollView(), ephemeral=True)



    
   # await interaction.response.send_message("Test Roll", view=DiceRollView(), ephemeral=True)


bot.run(TOKEN)