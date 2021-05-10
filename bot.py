#!/usr/bin/env python

import logging
import json
import csv
from threading import Timer
from typing import Optional
import urllib.request


from telegram import Update, ForceReply, Chat
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

watchers = []
last_contents = None

def start(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /start is issued."""

    chat: Chat = update.effective_chat
    if chat.id not in watchers:
        watchers.append(chat.id)

        file = open("watchers.json", "w")
        file.write(json.dumps(watchers))
        file.close()

    update.message.reply_markdown_v2(
        fr"Hi\. Du bekommst jetzt alle Updates\!"
    )


def help_command(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    global last_contents
    update.message.reply_text('Help!')
    last_contents = "lul"

def notifyWatchers(updater: Updater, impfidenz: Optional[float]):
    global watchers
    text = "Das Impfdashboard wurde aktualisiert 🎉!\n"
    if impfidenz is not None:
        text += "Die heutige bundesweite _7-Tage-Impfidenz_ (Erstimpfungen / Hunderttausend Einwohner und 7 Tage) beträgt:\n"
        text += f"*{impfidenz:.2f}*\n"
    text += "[https://impfdashboard.de](https://impfdashboard.de)"
    for watcher in watchers:
        updater.bot.send_message(chat_id=watcher, text=text, parse_mode='Markdown')


def get_impfidenz(csv_file):
    reader = csv.reader(csv_file, delimiter="\t")
    rows = []
    for row in reader:
        rows.append(row)
    index = -1
    for i in range(len(rows[0])):
        if rows[0][i] == "dosen_erst_differenz_zum_vortag":
            index = i
            break
    impfidenz = sum(int(rows[i][index]) for i in range(-7, 0))
    return impfidenz / (7. * 831.57201)

def poll_impfdashboard(updater: Updater):
    global last_contents
    print("Polling impfdashboard...")
    try:
        url = 'https://impfdashboard.de/static/data/germany_vaccinations_timeseries_v2.tsv'
        response = urllib.request.urlopen(url)
        lines = [l.decode('utf-8') for l in response.readlines()]
        contents = '\n'.join(lines)
        
        if last_contents is not None:
            if contents != last_contents:
                impfidenz = None
                try:
                    impfidenz = get_impfidenz(lines)
                finally:
                    notifyWatchers(updater, impfidenz)
        last_contents = contents
    except Exception as e:
        logger.log(level=logging.ERROR, msg=e)
    finally:
        Timer(15, poll_impfdashboard, [updater]).start()


def main() -> None:
    """Start the bot."""
    global watchers
    token = open("token.txt", "r").readline()
    watchers = json.loads(open("watchers.json", "r").read())

    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))

    updater.start_polling()
    poll_impfdashboard(updater)
    
    updater.idle()


if __name__ == '__main__':
    main()
