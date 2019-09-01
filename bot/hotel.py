import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Location
from telegram.ext import (Updater, CommandHandler, MessageHandler, CallbackQueryHandler, TypeHandler, Filters,
                          ConversationHandler)

from telegramcalendar import create_calendar, process_calendar_selection

logger = logging.getLogger("rafiq.hotel")

# States
CHOOSE_DESTINATION = 0
CHOOSE_DATE_ARRIVAL = 1
CHOOSE_DATE_DEPARTURE= 2
SELECTING_POI = 3

REGULAR_DESTINATIONS = ["Berlin", "London", "Paris", "Heilbronn"]
keyboard_destination_layout = [[b] for b in REGULAR_DESTINATIONS]
custom_dest_str = "Somewhere else..."
keyboard_destination_layout += [[custom_dest_str]]

regex_regular_choice_destination_filter = \
    "^(%s)$" % ("|".join(REGULAR_DESTINATIONS,))

markup_destination = ReplyKeyboardMarkup(keyboard_destination_layout, one_time_keyboard=True)


class HotelHandler():

    def __init__(self, bot):
        self.bot = bot

    def start(self, update, context):
        logger.info("Start hotel assistant.")
        update.message.reply_text(
            "Hi! I am your personal accomodation assistant. "+
            "I will ask you several questions about your trip.")
        update.message.reply_text("Where do you want to go to?",
            reply_markup=markup_destination)

        return CHOOSE_DESTINATION

    def regular_choice_destination(self, update, context):
        text = update.message.text
        context.user_data['choice'] = text
        logger.info("User selected '%s'" % text)
        update.message.reply_text("Cool, you selected %s!" % text)

        update.message.reply_text("Now, select the date when you arrive in %s!" % text,
                            reply_markup=create_calendar())
        return CHOOSE_DATE_ARRIVAL

    def custom_choice_destination(self, update, context):
        update.message.reply_text("Those are nice cities, please share where do you want to go?")
        return CHOOSE_DESTINATION

    def choose_date_arrival(self, update, context):
        selected, date = process_calendar_selection(self.bot, update)
        if selected:
            self.bot.send_message(chat_id=update.callback_query.from_user.id,
                            text="You selected %s" % (date.strftime("%a, the %d %B %Y")),
                            reply_markup=ReplyKeyboardRemove())

            
            self.bot.send_message(chat_id=update.callback_query.from_user.id, text="Now the departure date...", reply_markup=create_calendar())
            return CHOOSE_DATE_DEPARTURE
        else:
            return CHOOSE_DATE_ARRIVAL


    def choose_date_departure(self, update, context):
        selected, date = process_calendar_selection(self.bot, update)
        if selected:
            self.bot.send_message(chat_id=update.callback_query.from_user.id,
                            text="You selected %s" % (date.strftime("%a, the %d %B %Y")),
                            reply_markup=ReplyKeyboardRemove())

            
            self.bot.send_message(chat_id=update.callback_query.from_user.id, text="Done!")
            return ConversationHandler.END
        else:
            return ConversationHandler.END

    def done(self, update, context):
        return ConversationHandler.END


    def get_handler(self):
        # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
        return ConversationHandler(
            entry_points=[CommandHandler('hotel2', self.start)],

            states={
                CHOOSE_DESTINATION: [MessageHandler(Filters.regex("^(?!.*(%s))" % custom_dest_str),
                                            self.regular_choice_destination),
                            MessageHandler(Filters.regex('^%s$' % custom_dest_str), self.custom_choice_destination)
                            ],
                CHOOSE_DATE_ARRIVAL: [CallbackQueryHandler(self.choose_date_arrival)
                            ],
                CHOOSE_DATE_DEPARTURE: [CallbackQueryHandler(self.choose_date_arrival)
                            ],
            },

            fallbacks=[MessageHandler(Filters.regex('^Done$'), self.done)]
        )