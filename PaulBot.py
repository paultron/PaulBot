import discord
from discord.ext import commands

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


driver = "{ODBC Driver 18 for SQL Server}"

CONSTR = f'DRIVER={driver};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;Encrypt=no;'

CNXN = None
cursor = None


def connectServer() -> pyodbc.Connection:
    _cnx = pyodbc.connect(CONSTR)
    print(f"connected to {DATABASE}")
    return _cnx

@bot.event
async def on_ready():
    _synched = await bot.tree.sync()
    CNXN = connectServer()
    cursor = CNXN.cursor()

    cursor.execute("SELECT CustomerId, Name FROM dbo.Customers")

    row = cursor.fetchone()

    if row:
        print(row)

    print(f'We have logged in as {bot.user}')



class RitualDrop(discord.ui.Select):
    def __init__(self):

        options = [ 
            discord.SelectOption(label="Join", description="Add info to db", ), 
            discord.SelectOption(label="Sacrifice Firstborn", description="Who needs children?"),
            discord.SelectOption(label="Make Offering", description="Give an item of value.")
                ]
        super().__init__(placeholder="Which ritual to perform?",options=options)

    async def select_callback(self, select, interaction):

        if select.values[0] == select.options[0].label:
            print("joined")
            print("user id:", interaction.user.id)
            print("username:", interaction.user.name)

        await interaction.response.edit_message(content="A good choice.",view=None)
        

class RitualView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)       
        self.add_item(RitualDrop())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=3, disabled=False, emoji="✖️")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelled", view=None)


@bot.tree.command(name = "ritual", description = "Perform ceremony")
async def ritualcommand(interaction: discord.Interaction):
   await interaction.response.send_message("Welcome to PaulWorld, Pick an action", view=RitualView(), ephemeral=True)

bot.run(TOKEN)