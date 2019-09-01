import dotenv
dotenv.load_dotenv()

from datetime import datetime, date
import argparse
import logging
import os, sys
from typing import Union
import logging
import traceback
import time
from functools import wraps

import pytz 
from jinja2 import Environment, FileSystemLoader
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ChatAction
from telegram import ParseMode
import requests
import shapely
from pyproj import Transformer
from flatdict import FlatDict
import pandas as pd

sys.path.append(".")
from bot.gmaps import get_locatation_attributes, get_distances
from bot.booking import get_cheapest_nearby_hotels
from bot.utils import haversine
from bot.hotel import HotelHandler

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger("rafiq")


# load Jinja
file_loader = FileSystemLoader("bot/templates/")
env = Environment(loader=file_loader)


DT_FORMAT = "%Y-%m-%d"


def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        def command_func(update, context, *args, **kwargs):
            context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return func(update, context,  *args, **kwargs)
        return command_func
    
    return decorator


def get_hotels_with_distance(dest:str, date_arrival:datetime, date_departure:datetime, box_edge:int):

    dest_info = get_locatation_attributes(dest)
    dest_loc = dest_info["geometry"]["location"]
    dest_loc = (dest_loc["lat"], dest_loc["lng"])

    dt_departure = datetime(date_departure.year, date_departure.month, date_departure.day, 21, 0, 0)
    df_hotels = get_cheapest_nearby_hotels(loc=dest_loc, t_arrival=date_arrival, t_departure=dt_departure)

    destinations = [(r["latitude"], r["longitude"]) for _, r in df_hotels.iterrows()]

    df_distances = get_distances(origin=dest_loc, destinations=destinations, departure_time=date_departure)

    df_final = df_hotels.join(df_distances)

    _haverside_lambda = lambda row: haversine(row["latitude"], row["longitude"], dest_loc[0], dest_loc[1])
    df_final["haversine_distance"] = df_final[["latitude", "longitude"]].apply(_haverside_lambda, axis=1)

    df_final["duration_in_traffic_min"] = df_final["duration_in_traffic.value"]//60

    df_final = df_final.sort_values(["duration_in_traffic_min", "min_total_price"])

    return df_final


@send_action(ChatAction.TYPING)
def help(update, context):
    time.sleep(0.5)
    template = env.get_template("help.md")
    update.message.reply_text(template.render(), parse_mode=ParseMode.MARKDOWN)


@send_action(ChatAction.TYPING)
def alive(update, context):
    time.sleep(1)
    update.message.reply_text("I am alive!")

@send_action(ChatAction.TYPING)
def hotel(update, context):
    parser = _get_argparser()

    message = update.message.text
    message = message.split("/hotel")[-1].strip()

    logger.info("Received text: %s" % message)
    # update.message.reply_text("Please wait for a moment ...")
    try:
        
        args = parser.parse_args(message.split())
        dest = args.destination
        date_arrival = datetime.strptime(args.date_arrival, DT_FORMAT)
        date_departure = datetime.strptime(args.date_departure, DT_FORMAT)
        box_edge = args.box_edge

        df = get_hotels_with_distance(dest, date_arrival, date_departure, box_edge)

        lines = ["*{:s}* ([link]({:s})):\n\n*€{:.2f}* pro Nacht, {:d}min vom Zentrum entfernt.\n\n".format(r["hotel_name"], r["url"], r["min_total_price"], r["duration_in_traffic_min"]) for _, r in df.iterrows()]

        for l in lines[:5]:
            update.message.reply_text(l, parse_mode=ParseMode.MARKDOWN)
        #resp_str = "\n".join(lines)
        #update.message.reply_text(resp_str)
        
    except Exception as err:
        logger.error(str(err) + "\n" + traceback.format_exc())
        first_name = update.message.chat.first_name
        feeling = u'\U0001F614'
        out_msg = "Hey {:s}, ein Fehler ist aufgetreten ... {:s}".format(first_name, feeling)
        update.message.reply_text(out_msg)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def _get_argparser():
    parser = argparse.ArgumentParser(description='uni-unterkunft')

    parser.add_argument("destination", type=str, default="Stuttgart", help="uni location")
    parser.add_argument("date_arrival", type=str, default="Stuttgart", help="day of arrival in %s format" % DT_FORMAT)
    parser.add_argument("date_departure", type=str, default="Stuttgart", help="day of departure in %s format" % DT_FORMAT)
    parser.add_argument("--box_edge", type=int, help="bounding box edge length in meters", default=25000)
    return parser


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(os.environ["TELEGRAM_BOT_TOKEN"], use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("hotel", hotel))
    dp.add_handler(CommandHandler("alive", alive))

    hotel_handler = HotelHandler(updater.bot)
    dp.add_handler(hotel_handler.get_handler())

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("help", help))

    # log all errors
    dp.add_error_handler(error)

    logger.info("Bot is up and running!")

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
