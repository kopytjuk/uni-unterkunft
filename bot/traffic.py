import logging
from datetime import datetime, timedelta

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Location, ChatAction, ParseMode
from telegram.ext import (Updater, CommandHandler, MessageHandler, CallbackQueryHandler, TypeHandler, Filters,
                          ConversationHandler)

from bot.gmaps import gmaps
from bot.utils import haversine, send_action, jinja_env

logger = logging.getLogger("rafiq.traffic")

REGULAR_DESTINATIONS = ["🏡 Home", "🏭 Work", "🎓 University", "🏋 Gym"]
keyboard_destination_layout = [[b] for b in REGULAR_DESTINATIONS]
custom_dest_str = "🤔 Somewhere else..."
keyboard_destination_layout += [[custom_dest_str]]

regex_regular_choice_destination_filter = \
    "^(%s)$" % ("|".join(REGULAR_DESTINATIONS,))

markup_destination = ReplyKeyboardMarkup(keyboard_destination_layout, one_time_keyboard=True)

# States
CHOOSE_DESTINATION = 0
GET_CURRENT_LOCATION = 1

# bot global vars
destination_coordinates = None

def start(update, context):
    logger.info("Start traffic assistant.")

    template = jinja_env.get_template("traffic.md")
    update.message.reply_text(template.render(), parse_mode=ParseMode.MARKDOWN)

    update.message.reply_text("Your destination, my dear?",
        reply_markup=markup_destination)
    return CHOOSE_DESTINATION

def select_destination(update, context):

    global destination_coordinates

    text = update.message.text
    if "Work" in text:
        destination_coordinates = (49.080233, 9.308617)
    elif "Home" in text:
        destination_coordinates = (49.147072, 9.226154)
    elif "University" in text:
        destination_coordinates = (48.744962, 9.321983)
    elif "Gym" in text:
        destination_coordinates = (49.149416, 9.213681)
    
    update.message.reply_text("Got it!")

    update.message.reply_text("Where are you in the moment?\n\nShare your location! 🗺️ 📍")
    return GET_CURRENT_LOCATION


def get_current_location(update, context):
    loc = update.message.location

    user_lat, user_lng = loc.latitude, loc.longitude
    logger.info("Received location from user: lat=%.4f lng=%.4f" % (user_lat, user_lng))
    
    update.message.reply_text("Got it!")

    dest_lat, dest_lng = destination_coordinates

    context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)

    res = gmaps.distance_matrix((user_lat, user_lng), (dest_lat, dest_lng),
                mode="driving", units="metric", 
                departure_time=datetime.now()+timedelta(seconds=10))

    logger.info("GMAPS distances result: %s" % str(res))

    if len(res["rows"][0]["elements"]) < 1:
        update.message.reply_text("Houston, we have a problem! Exiting ...")
    else:
        first_res = res["rows"][0]["elements"][0]

        template = jinja_env.get_template("traffic_result.md")

        update.message.reply_text(template.render({"duration": first_res["duration"]["text"], "duration_in_traffic": first_res["duration_in_traffic"]["text"]}), parse_mode=ParseMode.MARKDOWN)

        return ConversationHandler.END


def done(update, context):
    return ConversationHandler.END

traffic_handler = ConversationHandler(
    entry_points=[CommandHandler('traffic', start)],
    states={
        CHOOSE_DESTINATION: [MessageHandler(Filters.regex("^(?!.*(%s))" % custom_dest_str),
                                 select_destination),
                    ],
        GET_CURRENT_LOCATION: [MessageHandler(Filters.location, get_current_location)]
    },

    fallbacks=[MessageHandler(Filters.regex('^Done$'), done)])
