import logging

from pajbot.modules import BaseModule, ModuleSetting
from pajbot.models.command import Command

log = logging.getLogger(__name__)

class AsciiProtectionModule(BaseModule):

    ID = __name__.split('.')[-1]
    NAME = 'Ascii Protection'
    DESCRIPTION = 'Times out users who post messages that contain too many ASCII characters.'
    SETTINGS = [
            ModuleSetting(
                key='min_msg_length',
                label='Minimum message length to be considered bad',
                type='number',
                required=True,
                placeholder='',
                default=70,
                constraints={
                    'min_value': 20,
                    'max_value': 1000,
                    }),
            ModuleSetting(
                key='timeout_length',
                label='Timeout length',
                type='number',
                required=True,
                placeholder='Timeout length in seconds',
                default=120,
                constraints={
                    'min_value': 30,
                    'max_value': 3600,
                    })
                ]

    def __init__(self):
        super().__init__()
        self.bot = None

    def on_pubmsg(self, source, message):
        if len(message) > self.settings['min_msg_length'] and source.level < 500 and source.moderator is False:
            non_alnum = sum(not c.isalnum() for c in message)
            ratio = non_alnum / len(message)
            if (len(message) > 240 and ratio > 0.82) or ratio > 0.93:
                duration, punishment = self.bot.timeout_warn(source, self.settings['timeout_length'])
                if duration > 0:
                    self.bot.whisper(source.username, 'You have been {punishment} because your message contained too many ascii characters.'.format(punishment=punishment))
                return False

    def enable(self, bot):
        if bot:
            bot.add_handler('on_pubmsg', self.on_pubmsg)
            self.bot = bot

    def disable(self, bot):
        if bot:
            bot.remove_handler('on_pubmsg', self.on_pubmsg)
