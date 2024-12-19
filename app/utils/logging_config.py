import logging

def setup_logging():
    # Clear all existing handlers
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    # Configure logging format
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Set specific loggers to ERROR to reduce noise
    for logger_name in [
        'discord',
        'discord.http',
        'discord.gateway',
        'discord.client',
        'discord.voice_client',
        'asyncio',
        'websockets'
    ]:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    # Set our app loggers to INFO
    for logger_name in ['music.cog', 'queue.view', 'now_playing.view']:
        logging.getLogger(logger_name).setLevel(logging.INFO) 