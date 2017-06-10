import hashlib
import random
import rsa
from base64 import b64encode
import requests
import datetime
import binascii
import time
import threading
from threading import Timer
from tkinter import *
import tkinter.scrolledtext as tkst
from decimal import Decimal

# Tkinter Stuff
VERSION = 0.5
TITLE = "WoodenWalit v{}".format(VERSION)

WIDTH = 600
HEIGHT = 400

root = Tk()
root.title(TITLE)
root.maxsize(WIDTH, HEIGHT)
root.minsize(WIDTH, HEIGHT)
root.resizable(0, 0)

root.iconbitmap('icon.ico')

border = Label(root, background='green')
border.place(x=245, y=25, width=330, height=350)

log = tkst.ScrolledText(root)
log.place(x=250, y=30, width=320, height=340)
log.configure(state='disabled')

beginning_time = time.monotonic()
idle_time = 0
time_string = StringVar()

time_label = Label(root, textvariable=time_string, font=("Courier New", 14), anchor=W)
time_label.place(x=20, y=160, width=220, height=30)

mining = True

def update_time():
    if mining:
        current_time = time.monotonic()
        subtracted_time = (current_time - beginning_time) - idle_time
        formatted_time = datetime.timedelta(seconds=round(subtracted_time))
        time_string.set("Time Mined: {}".format(formatted_time))

    t = Timer(1, update_time)
    t.setDaemon(True)
    t.start()

update_time()

mined = Label(root, text="Coins Mined: 0", font=("Courier New", 14), anchor=W)
mined.place(x=20, y=180, width=220, height=30)

total = Label(root, text="Total Coins: 0", font=("Courier New", 14), anchor=W)
total.place(x=20, y=200, width=220, height=30)

failed = Label(root, text="Failed Attempts: 0", font=("Courier New", 14), anchor=W)
failed.place(x=20, y=220, width=220, height=30)

def startStop():
    global mining
    global idle_time
    global stop_time
    if mining:
        guiprint("Idling...\n")
        border["bg"] = "red"
        start_stop["text"] = "Start Mining"
        stop_time = time.monotonic()
        mining = False
    else:
        guiprint("Starting...\n")
        border["bg"] = "green"
        start_stop["text"] = "Stop Mining"
        idle_time += time.monotonic() - stop_time
        mining = True

start_stop = Button(root, text="Stop Mining", font=("Courier New", 16), command=startStop)
start_stop.place(x=30, y=30, width=190, height=60)

data = {"mined":0, "total":0, "failed":0}

try:
    open("private_coin_storage.txt", "x").close()
except FileExistsError:
    pass

with open("private_coin_storage.txt", "r") as myfile:
    for line in myfile.readlines():
        data["total"] += int(line.split('\t')[0])

def updateData():
    mined["text"] = "Coins Mined: {}".format(data["mined"])
    total["text"] = "Total Coins: {}".format(data["total"])
    failed["text"] = "Failed Attempts: {}".format(data["failed"])

updateData()

# Print to tkinter window
def guiprint(message):
    log.configure(state='normal')
    log.insert(END, message + "\n")
    log.configure(state='disabled')
    log.see("end")

# Start of actual mining, Aaron's code
def mine():
    def bin2hex(binStr):
        return binascii.hexlify(binStr)

    keysize = 2048

    bank_url = 'http://104.199.121.149:8228'

    def updateGlobalTarget():
        global global_target

        guiprint('Syncing with global target...')
        response = requests.get(bank_url+'/global_target')
        global_target = float(response.text)
        guiprint(response.text + "\n")

    updateGlobalTarget()
    last_checked_minute = datetime.datetime.now().minute

    (mining_public_key, mining_private_key) = rsa.newkeys(keysize)
    mining_public_key_hex = bin2hex(mining_public_key.exportKey('DER')).decode('utf-8')
    mining_private_key_hex = bin2hex(mining_private_key.exportKey('DER')).decode('utf-8')

    guiprint("Starting to mine..." + "\n")

    last_won_time = datetime.datetime.now()

    while True:

        if mining == False:
            last_won_time = datetime.datetime.now()
            time.sleep(1)
            continue

        mined_nonce = str(random.randrange(1e16)).zfill(16)
        mined_coin_raw = mining_public_key_hex+'_'+mined_nonce
        mined_coin_hash = hashlib.sha256(mined_coin_raw.encode('utf-8')).hexdigest()
        mined_coin_hash_int = int(mined_coin_hash, 16)

        if mined_coin_hash_int < global_target:

            # For kicks, display the shiny new coin!
            guiprint("Found a coin! ({})".format('%e' % Decimal(mined_coin_hash_int)))

            # Sign the raw coin so that Banks can verify that I own the private key
            guiprint('Signing...')
            signature = b64encode(rsa.sign(mined_coin_raw.encode('utf-8'), mining_private_key, "SHA-256")).decode('utf-8')

            # Submit the new coin
            guiprint('Contacting server...')

            response = requests.post(bank_url+'/submit', json={
                'mined_coin_raw': mined_coin_raw,
                'signature': signature
            })
            guiprint(response.text)

            # Check that the submission was successful
            if response.text[:9] != 'Congrats!':
                updateGlobalTarget()
                last_checked_minute = now_minute
                data["failed"] += 1
                updateData()
                continue
            else:
                data["mined"] += 1
                data["total"] += 1
                updateData()

            # Display the time taken to min that coin
            now_time = datetime.datetime.now()

            d1_ts = time.mktime(last_won_time.timetuple())
            d2_ts = time.mktime(now_time.timetuple())

            guiprint('TIME: {} seconds'.format(d2_ts-d1_ts))

            last_won_time = now_time

            # Save the cheque
            with open("private_coin_storage.txt", "a+") as myfile:
                string  = '1' + '\t'
                string += mining_public_key_hex + '\t'
                string += mined_nonce + '\t'
                string += mining_private_key_hex + '\n'
                myfile.write(string)

            # Regenerate keys
            (mining_public_key, mining_private_key) = rsa.newkeys(keysize)
            mining_public_key_hex = bin2hex(mining_public_key.exportKey('DER')).decode('utf-8')
            mining_private_key_hex = bin2hex(mining_private_key.exportKey('DER')).decode('utf-8')

            guiprint('\n')

        now_minute = datetime.datetime.now().minute

        if now_minute % 1 == 0 and now_minute != last_checked_minute:
            updateGlobalTarget()
            last_checked_minute = now_minute

t = threading.Thread(target=mine)
t.setDaemon(True)
t.start()
root.mainloop()
