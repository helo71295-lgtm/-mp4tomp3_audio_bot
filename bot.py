import os
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
# Fixed import for MoviePy 2.0+
from moviepy import VideoFileClip

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fetch Telegram Bot Token from environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def post_init(application) -> None:
    """Sets up the bot command menu button in Telegram UI upon startup."""
    commands = [
        BotCommand("start", "Start the bot & show info"),
        BotCommand("help", "How to convert MP4 to MP3"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot command menu button updated successfully.")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message on /start command."""
    user = update.effective_user.first_name
    await update.message.reply_text(
        f"Hello {user}! 👋\n\n"
        "Send or forward me any MP4 video or video note, and I will convert it into an MP3 audio file for you."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends helpful instructions on /help command."""
    await update.message.reply_text(
        "💡 **How to use this bot:**\n\n"
        "1. Send any video file (MP4 format or Telegram video note).\n"
        "2. Wait a few seconds while the bot extracts the audio.\n"
        "3. Receive your MP3 file directly in the chat!\n\n"
        "If you encounter any issues, make sure your file contains an audio stream."
    )


async def convert_video_to_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming videos and converts MP4 to MP3."""
    message = update.message
    video = message.video or message.video_note or message.document

    # Send typing status indicator
    await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
    status_msg = await message.reply_text("📥 Downloading video file...")

    video_path = f"video_{message.message_id}.mp4"
    audio_path = f"audio_{message.message_id}.mp3"

    try:
        # Download the video file from Telegram
        file = await context.bot.get_file(video.file_id)
        await file.download_to_drive(video_path)

        await status_msg.edit_text("🔄 Converting MP4 to MP3...")

        # Process conversion with MoviePy 2.0+
        clip = VideoFileClip(video_path)
        if clip.audio is None:
            await status_msg.edit_text("❌ Error: This video file contains no audio stream.")
            clip.close()
            return

        # Write audio file (removed deprecated logger argument)
        clip.audio.write_audiofile(audio_path)
        clip.close()

        await status_msg.edit_text("📤 Uploading MP3 audio...")

        # Send converted audio back to user
        with open(audio_path, "rb") as audio_file:
            await message.reply_audio(
                audio=audio_file,
                title=f"Converted_Audio_{message.message_id}",
                filename="converted_audio.mp3"
            )

        await status_msg.delete()

    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        await status_msg.edit_text(f"❌ Failed to process video: {str(e)}")

    finally:
        # Clean up local temporary files
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)


def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable missing!")
        return

    # Build the Application with post_init hook
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Add Command & Message Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE | filters.Document.VIDEO, convert_video_to_audio))

    logger.info("Bot started successfully...")
    app.run_polling()


if __name__ == "__main__":
    main()
