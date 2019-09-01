import dotenv
dotenv.load_dotenv()

import os, sys
import logging

from telegram.ext import Updater, CommandHandler
from telegram import ChatAction
from telegram import ParseMode

sys.path.append(".")
from bot.hotel import hotel_handler
from bot.utils import send_action, jinja_env

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger("rafiq")

@send_action(ChatAction.TYPING)
def help(update, context):
    template = jinja_env.get_template("help.md")
    update.message.reply_text(template.render(), parse_mode=ParseMode.MARKDOWN)

@send_action(ChatAction.TYPING)
def alive(update, context):
    update.message.reply_text("I am alive!")

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(os.environ["TELEGRAM_BOT_TOKEN"], use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("alive", alive))

    # add hotel handler
    dp.add_handler(hotel_handler)

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
