import logging
from functools import wraps
from datetime import datetime

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Location, ChatAction, ParseMode
from telegram.ext import (Updater, CommandHandler, MessageHandler, CallbackQueryHandler, TypeHandler, Filters,
                          ConversationHandler)

from bot.telegramcalendar import create_calendar, process_calendar_selection
from bot.gmaps import get_locatation_attributes, get_distances
from bot.booking import get_cheapest_nearby_hotels
from bot.utils import haversine, send_action, jinja_env

logger = logging.getLogger("rafiq.hotel")

_query = {"location": None, "arrival_date": None, "departure_date": None}

# States
CHOOSE_DESTINATION = 0
CONFIRM_DESTINATION = 1
CHOOSE_DATE_ARRIVAL = 2
CHOOSE_DATE_DEPARTURE = 3
CHOOSE_TRAVEL_MODE = 4
CONFIRM_QUERY = 99

REGULAR_DESTINATIONS = ["Berlin", "London", "Paris", "Heilbronn"]
keyboard_destination_layout = [[b] for b in REGULAR_DESTINATIONS]
custom_dest_str = "Somewhere else..."
keyboard_destination_layout += [[custom_dest_str]]

regex_regular_choice_destination_filter = \
    "^(%s)$" % ("|".join(REGULAR_DESTINATIONS,))

markup_destination = ReplyKeyboardMarkup(keyboard_destination_layout, one_time_keyboard=True)

markup_confirm = ReplyKeyboardMarkup([["OK"], ["CANCEL"]], one_time_keyboard=True)
markup_travel_mode = ReplyKeyboardMarkup([["Car"], ["Public transport"], ["Walking"]], one_time_keyboard=True)


def get_hotels_with_distance(lat, lng, date_arrival:datetime, date_departure:datetime, box_edge:int=25000):

    dest_loc = (lat, lng)

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

def start(update, context):
    logger.info("Start hotel assistant.")
    update.message.reply_text(
        "Hi! I am your personal accomodation assistant. "+
        "I will ask you several questions about your trip.")
    update.message.reply_text("Where do you want to go to?",
        reply_markup=markup_destination)

    return CHOOSE_DESTINATION

def regular_choice_destination(update, context):
    text = update.message.text
    context.user_data['choice'] = text
    logger.info("User selected '%s'" % text)

    update.message.reply_text("Please confirm the following location:")

    dest_info = get_locatation_attributes(text)
    dest_loc = dest_info["geometry"]["location"]
    context.bot.send_location(chat_id=update.message.from_user.id, latitude=dest_loc["lat"], longitude=dest_loc["lng"],
                               reply_markup=markup_confirm)
    _query["location"] = dest_info
    return CONFIRM_DESTINATION

def custom_choice_destination(update, context):
    update.message.reply_text("Those are nice cities, please share where do you want to go?")
    return CHOOSE_DESTINATION

def confirm_destination(update, context):
    text = update.message.text
    if text == "OK":
        update.message.reply_text("Please select date of arrival:",
                                  reply_markup=create_calendar())
        return CHOOSE_DATE_ARRIVAL
    else:
        update.message.reply_text("Where do you want to go to?",
                                  reply_markup=markup_destination)
        return CHOOSE_DESTINATION

def choose_date_arrival(update, context):
    selected, date = process_calendar_selection(context.bot, update)
    if selected:
        context.bot.send_message(chat_id=update.callback_query.from_user.id,
                            text="You selected %s" % (date.strftime("%a, the %d %B %Y")),
                            reply_markup=ReplyKeyboardRemove())
        _query["dt_arrival"] = date

        context.bot.send_message(chat_id=update.callback_query.from_user.id, text="Now the departure date...",
                                  reply_markup=create_calendar())
        return CHOOSE_DATE_DEPARTURE
    else:
        return CHOOSE_DATE_ARRIVAL


def choose_date_departure(update, context):
    selected, date = process_calendar_selection(context.bot, update)
    if selected:
        context.bot.send_message(chat_id=update.callback_query.from_user.id,
                            text="You selected %s" % (date.strftime("%a, the %d %B %Y")),
                            reply_markup=ReplyKeyboardRemove())

        _query["dt_departure"] = date

        context.bot.send_message(chat_id=update.callback_query.from_user.id,
                                   text="What means of transport will you use?",
                                reply_markup=markup_travel_mode)
        return CHOOSE_TRAVEL_MODE
    else:
        return CHOOSE_DATE_DEPARTURE


def set_travel_mode(update, context):
    text = update.message.text
    if text=="Car":
         _query["mode"] = "driving"#
         _query["mode_human"] = "Car"
    elif text == "Public transport":
         _query["mode"] = "transit"
         _query["mode_human"] = "Public transport"
    elif text == "Walking":
         _query["mode"] = "walking"
         _query["mode_human"] = "Walking"

    template = jinja_env.get_template("query_confirm.md")
    summary_args = {"dest":  _query["location"]['formatted_address'],
                    "dt_arrival": _query["dt_arrival"].strftime("%a, %B %d, %Y"),
                    "dt_departure": _query["dt_departure"].strftime("%a, %B %d, %Y"),
                    "transport_mode": _query["mode_human"],
                    "max_travel_time": "20 min"}
    update.message.reply_text(template.render(**summary_args), parse_mode=ParseMode.MARKDOWN,
                              reply_markup=markup_confirm)
    return CONFIRM_QUERY

@send_action(ChatAction.TYPING)
def search_accomodation(update, context):

    dest_loc = _query["location"]["geometry"]["location"]

    df = get_hotels_with_distance(dest_loc["lat"], dest_loc["lng"], _query["dt_arrival"], _query["dt_departure"])

    lines = [
        "*{:s}* ([link]({:s})):\n\n*€{:.2f}* pro Nacht, {:d}min vom Zentrum entfernt.\n\n".format(r["hotel_name"],
                                                                                                  r["url"], r[
                                                                                                      "min_total_price"],
                                                                                                  r[
                                                                                                      "duration_in_traffic_min"])
        for _, r in df.iterrows()]

    for l in lines[:10]:
        update.message.reply_text(l, parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

def done(update, context):
    return ConversationHandler.END

hotel_handler = ConversationHandler(
    entry_points=[CommandHandler('hotel', start)],
    states={
        CHOOSE_DESTINATION: [MessageHandler(Filters.regex("^(?!.*(%s))" % custom_dest_str),
                                 regular_choice_destination),
                    MessageHandler(Filters.regex('^%s$' % custom_dest_str), custom_choice_destination)
                    ],
        CONFIRM_DESTINATION: [MessageHandler(Filters.regex("^(OK|Cancel)$"), confirm_destination)],
        CHOOSE_DATE_ARRIVAL: [CallbackQueryHandler(choose_date_arrival)
                    ],
        CHOOSE_DATE_DEPARTURE: [CallbackQueryHandler(choose_date_departure)
                    ],
        CHOOSE_TRAVEL_MODE: [MessageHandler(Filters.regex("^(Car|Public transport|Walking)$"), set_travel_mode)],
        CONFIRM_QUERY: [MessageHandler(Filters.regex("^(OK)$"), search_accomodation)]
    },

    fallbacks=[MessageHandler(Filters.regex('^Done$'), done)])
