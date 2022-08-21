from replit import db
import os
import discord
from googleapiclient.discovery import build
from google.oauth2 import service_account
import datetime
from keep_alive import keep_alive
import pytz
from discord.ext import commands, tasks

#-----------Google sheet Stuffs----------------#
# If modifying these scopes, delete the file token.json.
SERVICE_ACCOUNT_FILE = 'keys.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

creds = None
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = '14ZDwr58-hOv5RGnUEtHPXyvoAdO9IL6o5JVUIgkb0rU'

try:
  service = build('sheets', 'v4', credentials=creds)
except:
  DISCOVERY_SERVICE_URL = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
  service = build('sheets', 'v4', credentials=creds, discoveryServiceUrl=DISCOVERY_SERVICE_URL)

# Call the Sheets API
sheet = service.spreadsheets()

#-----------\Google sheet Stuffs ends----------------#

#-----------Initializing Discord Clients-------------#
# discord init
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="$$", intents=intents)
#-----------\Initializing Discord Clients ends-------------#

#-----------Commands That got fired on Message Event-------------#
@client.event
async def on_message(message):
  #Get the User+Id
  name = message.author.name +"#"+message.author.discriminator
  if message.author == client.user:
    return
    
  # Take Attendance with !!plan command
  if isValidCmd(message.content,"!!plan "):
    # removes the !!plan from the string
    st = " ".join(message.content.split(" ")[1:]).strip()
    try:
      # updates G Sheet and return True if success
      can_add = update_data(st,name,message.author.id)

      # responses to the plan command
      if can_add:
        await message.channel.send(":white_check_mark: Added New Entry"+ message.author.mention)
        await message.channel.send(":page_with_curl: \n**Here is your Entry:**\n"+get_data(name,1))

      # currentry never get executed as user cann add as many times as he wants tackled in update_data()
      else:
        await message.channel.send(":x: Something went wrong! Maybe you don't have a sheet on google sheets or Try Again "+ message.author.mention)

      # tackles the count change when update_data called
    except:
      db[name] = {"count":1 if db[name]["count"] == 1 else db[name]["count"]-1 ,"can_add":True,"last_row":0,"len":0,"final_added":False,"id":db[name]["id"]}
      await message.channel.send("Invalid Syntax or Something went wrong! Please Try again! "+message.author.mention)
      
  #shows the entries
  if isValidCmd(message.content,"!!show"):
    try:
      wanted = message.content[6:].strip()
      wanted = int(wanted) if len(wanted) else 0
      data_to_show = get_data(name ,wanted)
      # print(data_to_show)
      await message.channel.send(f":mailbox_with_no_mail: Here is your Entries\n{data_to_show if len(data_to_show) else 'Sorry! Nothing to show. Your entry is empty'}\n"+message.author.mention)
      
    except:
      await message.channel.send(":laughing: \nInvalid Syntax or Something went wrong!")
      
  #addes the daily update - can be changed as manay times as the user want
  if isValidCmd(message.content,"!!update"):
    st = message.content[8:].strip()
    if len(st):
      try:
        is_eligiable,can_add = add_final(name,st,message)
        if is_eligiable and not can_add:
          await message.channel.send("Your Update report added successfully "+message.author.mention)
          await message.channel.send(message.author.mention+ " Here is your entry:\n"+get_data(name,1))
        elif is_eligiable and can_add:
        
          await message.channel.send(":x: Sorry, Couldn't add your report in google sheet! something went wrong! Try again!")
          
        else:
          await message.channel.send("You have not yet added todays Planing, Can't update report "+message.author.mention)
      except:
        await message.channel.send("Something went Wrong Please Try again!")
        db[name]["final_added"] = False
    else:
      await message.channel.send("Plz Add valid Details! "+message.author.mention)
      

  if isValidCmd(message.content,"!!remove"):
    if not name in db.keys():
      await message.channel.send("Can't remove your entry in empty "+message.author.mention)

    else:
      if db[name]["final_added"]:
        await message.channel.send("Can't remove after adding final report "+message.author.mention)
      else:
        try:
          can_edit = edit_data(name,message)
          if can_edit:
            await message.channel.send(":bookmark_tabs:  removed last entry "+ message.author.mention)
          else:
            await message.channel.send("Nothing to edit! No entry Today "+message.author.mention)
        except:
          await message.channel.send("Something Went Wrong! Please Try Again! "+message.author.mention)

  
  if isValidCmd(message.content,"!!db"):
    # await message.channel.send(str(db[name]))
    print("something")
    for i in db.keys():
      await message.channel.send(str(db[i]))

  if isValidCmd(message.content,"!!clear"):
    await message.channel.send("Cleard Data")
    db.clear()


  if isValidCmd(message.content,"!!clearMyTodaysTask"):
    re_init(name)

  if isValidCmd(message.content, "!!help"):
    with open("help.txt","r") as help:
      msg = help.read()
      await message.channel.send(msg)

  if isValidCmd(message.content,"!!link"):
    await message.channel.send("> Google Sheet Link: **https://docs.google.com/spreadsheets/d/14ZDwr58-hOv5RGnUEtHPXyvoAdO9IL6o5JVUIgkb0rU**")

  if isValidCmd(message.content,"!!video"):
    await message.channel.send("Here is The tutorial below-\n"+"https://www.youtube.com/watch?v=q95fiRtkJdg")

#-----------Commands That got fired on Message Event ends-------------#

#-----------edit data function, edits the G Sheet-----------#


def edit_data(name,message):
  
  n = db[name]["last_row"]
  lines = db[name]["len"]
  if not n:
    return False
    
  data = [[""]*6]*lines
  
  service.spreadsheets().values().update(
    spreadsheetId=SPREADSHEET_ID,
    range=f"{name}!A{n}",
    valueInputOption="USER_ENTERED",
    body={
        "values": data
    }).execute()
  
  db[name]["count"] -= 1
  re_init(name)
  return True

#-------re_init the personal db--------#

def re_init(name,is_new=False,id=0):
  if is_new:
    
    db[name] = {
      "count":0,
      "can_add":True,
      "last_row":0,
      "len":0,
      "final_added":False,
      "id":id
    }
    return False
  
  db[name] = {
    "count":db[name]["count"],
    "can_add":True,
    "last_row":0,
    "len":0,
    "final_added":False,
    "id":db[name]["id"]
  }
  return True

#--------addes the update to the sheet------#
  
def add_final(name,study_update,message):
  if name in db.keys():
    if db[name]["can_add"]:
      return False,True
  else:
    return False,False

  bdTime = pytz.timezone("Asia/Dhaka")
  # datetime.today().strftime("%I:%M %p")
  time_date = datetime.datetime.now(bdTime).strftime("%Y-%m-%d - %I:%M %p")
  data = [[time_date,study_update]]

  try:
    service.spreadsheets().values().update(
      spreadsheetId=SPREADSHEET_ID,
      range=f"{name}!E{db[name]['last_row']}",
      valueInputOption="USER_ENTERED",
      body={
          "values": data
      }).execute()
  except:
    # await message.channel.send(":x: Sorry, Couldn't add your report in google sheet!")
    return True,True
  db[name]["final_added"] = True
  return True,False
  
  
##------gets the data from g sheet------#

def get_data(name,wanted=0):
  try: 
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range=name).execute()
  except:
    return ""
    
  values = result.get('values', [])
  items = []
  one_item = []
  for line in values[1:]:
    if line[0].strip() != "":
      if len(one_item):
        items.append(one_item)
      one_item =[]
    
    one_item.append(line)

  if len(one_item):
    items.append(one_item)

  entries = []
  data_to_show = ""

  for item in items[-wanted:]:
    if not len(item):
      continue
      
    data_to_show = ""
    data_to_show += f"**Date:** `{item[0][1]}`\n"
    data_to_show += "**Target:**\n> "
    if len(item[0]) < 6:
      item[0] = [*item[0][:2] , "","","No Update", "No Update"]
    for line in item[1:]:
      data_to_show += line[3].strip()+"\n------------\n> "
    data_to_show = data_to_show[:-2] # "> "
    data_to_show += f"**Update Time:** `{item[0][4]}`\n"
    temp = "\n> ".join(item[0][5].split("\n"))
    data_to_show += f"**Update:**\n> {temp}"
    entries.append(data_to_show)
  
  final_data = "\n`----------------------`\n".join(entries)
  if len(final_data)>=2000:
    n = 1
    cr = 0
    for i in range(len(entries)):
      n = i+1
      cr = len("\n`----------------------`\n".join(entries[-n:]))
      if cr >= 2000:
        n-=1
        break
    final_data = "\n`----------------------`\n".join(entries[-n:])
  return final_data
        
      
#-------updates data in g sheets------#

def update_data(st,name,id):
  try:
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                              range=name).execute()
  except:
    return False
    
  values = result.get('values', [])
  n = len(values) + 1
  bdTime = pytz.timezone("Asia/Dhaka")
  if name in db.keys():
    if not db[name]["can_add"]:
      data = []
      for i in st.split(";"):
        s = i.strip()
        if len(s):
          t=datetime.datetime.now(bdTime).strftime("%H:%M")
          data.append(["","",t,s])
      request = service.spreadsheets().values().update(
    spreadsheetId=SPREADSHEET_ID,
    range=f"{name}!A{n}",
    valueInputOption="USER_ENTERED",
    body={
        "values": data
    }).execute()
      db[name]["len"] += len(data)
      return True

    # db[name]["count"] += 1  
    # db[name]["can_add"] = False
  else:
    re_init(name,True,id)

  time_date = datetime.datetime.now(bdTime).strftime("%Y-%m-%d")
  topics = st.split(";")
  data = [[str(db[name]["count"]+1),time_date]]
  t=datetime.datetime.now(bdTime).strftime("%H:%M")
  for i in topics:
    s = i.strip()
    if len(s):
      data.append(["","",t,s])

  db[name]["last_row"] = n
  db[name]["len"] = len(data)
  try:
    service.spreadsheets().values().update(
      spreadsheetId=SPREADSHEET_ID,
      range=f"{name}!A{n}",
      valueInputOption="USER_ENTERED",
      body={
          "values": data
      }).execute()
  except:
    re_init(name)
    return False
  db[name]["can_add"] = False
  db[name]["count"] +=1
  return True


#-------Schedule check if its time to add report and dms msgs-------#
@tasks.loop(minutes=10)
async def schedule_check():
  bdTime = pytz.timezone("Asia/Dhaka")
  hour = datetime.datetime.now(bdTime).strftime('%H')
  minutes = datetime.datetime.now(bdTime).strftime('%M')

  #re_init daily permission or starts new day
  if int(hour) == 0:
    if 0 <= int(minutes) <= 10:
      for i in db.keys():
        await sendDm(db[i]["id"],"Started New Day! Good Luck, Let's crack the Addmission")
        re_init(i)
  #checks if added daily update
  if int(hour) == 23:
    if 40 <=int(minutes) <= 60:
        if not db[i]["final_added"] and not db[i]["can_add"]:
          await sendDm(db[i]["id"],"অনুগ্রহপূর্বক আপনার Attendance Room এ আজকের দিনের লেখাপড়ার Update দেন! আপনার কাছ থেকে এখন পর্যন্ত আজকের দিনের কোন Update পাইনাই :unamused:")

  #checks if added daiy Plan
  if  7 <= int(hour) <= 10:
    if 0 <= int(minutes) <=20:
      for i in db.keys():
        if db[i]["can_add"]:
          await sendDm(db[i]["id"],"অনুগ্রহপূর্বক আপনার Attendance Room এ আজকের দিনের লেখাপড়ার Planning দেন! আপনার কাছ থেকে এখন পর্যন্ত আজকের দিনের কোন Planning পাইনাই :unamused: ")
      

#on bot ready
@client.event
async def on_ready():
  schedule_check.start()
  print(f"We have logged in as {client.user}")


#checks commands validity
def isValidCmd(st,cmd):
  if st.lower().startswith(cmd):
    return True
  return False

#sends dms based on id
async def sendDm(id,msg):
    user = await client.fetch_user(id)
    await user.send(msg) 
    


#------start executing with token------#
keep_alive()
token = os.environ["token"]
client.run(token)