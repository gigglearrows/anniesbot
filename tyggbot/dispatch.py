import math
import re
import logging
import collections
import json
import datetime
import random

import pylast


from tyggbot.models.user import User
from tyggbot.models.filter import Filter
from tyggbot.tbutil import time_limit, TimeoutException, time_since

from sqlalchemy import desc
from sqlalchemy import func

log = logging.getLogger('tyggbot')


def init_dueling_variables(user):
    if hasattr(user, 'duel_request'):
        return False
    user.duel_request = False
    user.duel_target = False
    user.duel_price = 0

def check_follow_age(bot, source, username):
    age = bot.twitchapi.get_follow_relationship(username, bot.streamer)
    if source.username == username:
        if age is False:
            bot.say('{}, you are not following {}'.format(source.username_raw, bot.streamer))
        else:
            bot.say('{}, you have been following {} for {}'.format(source.username_raw, bot.streamer, time_since(datetime.datetime.now().timestamp() - age.timestamp(), 0)))
    else:
        if age is False:
            bot.say('{}, {} is not following {}'.format(source.username_raw, username, bot.streamer))
        else:
            bot.say('{}, {} has been following {} for {}'.format(source.username_raw, username, bot.streamer, time_since(datetime.datetime.now().timestamp() - age.timestamp(), 0)))


class Dispatch:
    """
    Methods in this class accessible from commands
    """

    raffle_running = False

    def nl(bot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = bot.users.find(tmp_username)
            if user:
                username = user.username_raw
                num_lines = user.num_lines
            else:
                username = tmp_username
                num_lines = 0
        else:
            username = source.username_raw
            num_lines = source.num_lines

        phrase_data = {
                'username': username,
                'num_lines': num_lines
                }

        if num_lines > 0:
            bot.say(bot.phrases['nl'].format(**phrase_data))
        else:
            bot.say(bot.phrases['nl_0'].format(**phrase_data))
   
    def clear_lines_month(bot, source, message, event, args):
        #EDIT THIS SHITCURSOR
        #cursor = bot.get_dictcursor()
        #cursor.execute('UPDATE `tb_user` SET `num_lines_month`=0')
        bot.users.db_session.query(User).update({User.num_lines_month: 0}) 
             
        #for username, user in bot.users.items():
        #   user.num_lines_month = 0
        #    user.needs_sync = True
        log.info('Successfully cleared num_lines_month for this month')
      #  cursor.close()

    def point_pos(bot, source, message, event, args):
        user = None

        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = bot.users.find(tmp_username)

        if not user:
            user = source

        phrase_data = {
                'points': user.points
                }

        if user == source:
            phrase_data['username_w_verb'] = 'You are'
        else:
            phrase_data['username_w_verb'] = '{0} is'.format(user.username_raw)

        if user.points > 0:
            query_data = bot.users.db_session.query(func.count(User.id)).filter(User.points > user.points).one()
            phrase_data['point_pos'] = int(query_data[0]) + 1
            bot.whisper(source.username, bot.phrases['point_pos'].format(**phrase_data))

    def nl_pos(bot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = bot.users.find(tmp_username)
            if user:
                username = user.username_raw
                num_lines = user.num_lines
            else:
                username = tmp_username
                num_lines = 0
        else:
            username = source.username_raw
            num_lines = source.num_lines

        phrase_data = {
                'username': username,
                'num_lines': num_lines
                }

        if num_lines <= 0:
            bot.say(bot.phrases['nl_0'].format(**phrase_data))
        else:
            query_data = bot.users.db_session.query(func.count(User.id)).filter(User.num_lines > num_lines).one()
            phrase_data['nl_pos'] = int(query_data[0]) + 1
            bot.say(bot.phrases['nl_pos'].format(**phrase_data))

    def nl_pos_month(bot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = bot.users.find(tmp_username)
            if user:
                username = user.username_raw
                num_lines_month = user.num_lines_month
            else:
                username = tmp_username
                num_lines_month = 0
        else:
            username = source.username_raw
            num_lines_month = source.num_lines_month

        phrase_data = {
                'username': username,
                'num_lines_month': num_lines_month
                }

        if num_lines_month <= 0:
            bot.me('Volcania {0} has not written anything in this channel this month ... BibleThump'.format(username))
        else:
            #Check this CURSORSHIT
            query_data = bot.users.db_session.query(func.count(User.id)).filter(User.num_lines_month > num_lines_month).one()
            
            #cursor = bot.get_dictcursor()
            #cursor.execute('SELECT COUNT(*) as `pos` FROM `tb_user` WHERE `num_lines_month`>%s', (num_lines_month, ))
            #row = cursor.fetchone()
            #if row:
            #phrase_data['nl_pos_month'] = int(query_data[0]) + 1
            bot.me('Volcania {0} is rank # {1} on this months lines leaderboard! 4Head'.format(username, int(query_data[0] + 1)))

   

    def query(bot, source, message, event, args):
        if bot.wolfram is None:
            return False

        try:
            log.debug('Querying wolfram "{0}"'.format(message))
            res = bot.wolfram.query(message)

            x = 0
            for pod in res.pods:
                if x == 1:
                    res = '{0}'.format(' '.join(pod.text.splitlines()).strip())
                    log.debug('Answering with {0}'.format(res))
                    bot.say(res)
                    break

                x = x + 1
        except Exception as e:
            log.error('caught exception: {0}'.format(e))

    def math(bot, source, message, event, args):
        if message:
            message = message.replace('pi', str(math.pi))
            message = message.replace('e', str(math.e))
            message = message.replace('π', str(math.pi))
            message = message.replace('^', '**')
            message = message.replace(',', '.')
            res = '??'
            expr_res = None

            emote = 'Kappa'

            try:
                with time_limit(1):
                    expr_res = bot.tbm.eval_expr(''.join(message))
                    if expr_res == 69 or expr_res == 69.69:
                        emote = 'Kreygasm'
                    elif expr_res == 420 or expr_res == 420.0:
                        emote = 'CiGrip'
                    res = 'Volcania {2}, {0} {1}'.format(expr_res, emote, source.username)
            except TimeoutException as e:
                res = 'Volcania timed out DansGame'
                log.error('Timeout exception: {0}'.format(e))
            except Exception as e:
                log.error('Uncaught exception: {0}'.format(e))
                return

            bot.say(res)

    def multi(bot, source, message, event, args):
        if message:
            streams = message.strip().split(' ')
            if len(streams) == 1:
                streams.insert(0, bot.streamer)

            url = 'http://multitwitch.tv/' + '/'.join(streams)

            bot.say('Volcania {0}, {1}'.format(source.username, url))

    def ab(bot, source, message, event, args):
        if message:

            msg_parts = message.split(' ')
            if len(msg_parts) >= 2:
                outer_str = msg_parts[0]
                inner_str = ' {} '.format(outer_str).join(msg_parts[1:] if len(msg_parts) >= 3 else msg_parts[1])

                bot.say('{0}, {1} {2} {1}'.format(source.username, outer_str, inner_str))

                return True

        return False

    def abc(bot, source, message, event, args):
        return Dispatch.ab(bot, source, message, event, args)

    def silence(bot, source, message, event, args):
        bot.silent = True

    def unsilence(bot, source, message, event, args):
        bot.silent = False

    def add_banphrase(bot, source, message, event, args):
        """Dispatch method for creating and editing banphrases.
        Usage: !add banphrase BANPHRASE [options]
        Multiple options available:
        --length LENGTH
        --perma/--no-perma
        --notify/--no-notify
        """

        if message:
            options, response = bot.filters.parse_banphrase_arguments(message)

            if options is False:
                bot.whisper(source.username, 'Volcania Invalid banphrase')
                return False

            options['extra_args'] = {
                    'notify': options.get('notify', Filter.DEFAULT_NOTIFY),
                    'time': options.get('time', Filter.DEFAULT_TIMEOUT_LENGTH),
                    }

            is_perma = options.get('perma', None)
            if is_perma is True:
                options['action'] = {
                        'type': 'func',
                        'cb': 'ban_source'
                        }
            elif is_perma is False:
                options['action'] = {
                        'type': 'func',
                        'cb': 'timeout_source'
                        }

            # XXX: For now, we do .lower() on the banphrase.
            banphrase = response.lower()
            if len(banphrase) == 0:
                bot.whisper(source.username, 'Volcania No banphrase given')
                return False

            filter, new_filter = bot.filters.add_banphrase(banphrase, **options)

            if new_filter is True:
                bot.whisper(source.username, 'Volcania Inserted your banphrase (ID: {filter.id})'.format(filter=filter))
                return True

            options['extra_args'] = {}
            try:
                options['extra_args'] = json.loads(filter.extra_extra_args)
            except:
                pass

            if 'notify' in options:
                options['extra_args']['notify'] = options['notify']
            if 'time' in options:
                options['extra_args']['time'] = options['time']

            filter.set(**options)
            bot.whisper(source.username, 'Volcania Updated the given banphrase (ID: {filter.id}) with ({what})'.format(filter=filter, what=', '.join([key for key in options])))

    def add_win(bot, source, message, event, args):
        bot.kvi['br_wins'].inc()
        bot.me('Volcania {0} added a BR win!'.format(source.username))
        log.debug('{0} added a BR win!'.format(source.username))

    def add_command(bot, source, message, event, args):
        """Dispatch method for creating and editing commands.
        Usage: !add command ALIAS [options] RESPONSE
        Multiple options available:
        --whisper/--no-whisper
        --reply/--no-reply
        --modonly/--no-modonly
        --cd CD
        --usercd USERCD
        --level LEVEL
        --cost COST
        """

        if message:
            # Make sure we got both an alias and a response
            message_parts = message.split()
            if len(message_parts) < 2:
                bot.whisper(source.username, 'Volcania Usage: !add command ALIAS [options] RESPONSE')
                return False

            options, response = bot.commands.parse_command_arguments(message_parts[1:])

            if options is False:
                bot.whisper(source.username, 'Volcania Invalid command')
                return False

            alias_str = message_parts[0].replace('!', '').lower()
            type = 'say'
            if options['whisper'] is True:
                type = 'whisper'
            elif options['reply'] is True:
                type = 'reply'
            elif response.startswith('/me') or response.startswith('.me'):
                type = 'me'
                response = ' '.join(response.split(' ')[1:])
            elif options['whisper'] is False or options['reply'] is False:
                type = 'say'
            action = {
                    'type': type,
                    'message': response,
                    }

            command, new_command = bot.commands.create_command(alias_str, action=action, **options)
            if new_command is True:
                bot.whisper(source.username, 'Volcania Added your command (ID: {command.id})'.format(command=command))
                return True

            if len(action['message']) > 0:
                options['action'] = action
            elif not type == command.action.subtype:
                options['action'] = {
                        'type': type,
                        'message': command.action.response,
                        }
            bot.commands.edit_command(command, **options)
            bot.whisper(source.username, 'Volcania Updated the command (ID: {command.id})'.format(command=command))

    def add_funccommand(bot, source, message, event, args):
        """Dispatch method for creating and editing function commands.
        Usage: !add command ALIAS [options] CALLBACK
        Multiple options available:
        --cd CD
        --usercd USERCD
        --level LEVEL
        --cost COST
        --modonly/--no-modonly
        """

        if message:
            # Make sure we got both an alias and a response
            message_parts = message.split(' ')
            if len(message_parts) < 2:
                bot.whisper(source.username, 'Volcania Usage: !add funccommand ALIAS [options] CALLBACK')
                return False

            options, response = bot.commands.parse_command_arguments(message_parts[1:])

            if options is False:
                bot.whisper(source.username, 'Volcania Invalid command')
                return False

            alias_str = message_parts[0].replace('!', '').lower()
            action = {
                    'type': 'func',
                    'cb': response.strip(),
                    }

            command, new_command = bot.commands.create_command(alias_str, action=action, **options)
            if new_command is True:
                bot.whisper(source.username, 'Volcania Added your command (ID: {command.id})'.format(command=command))
                return True

            if len(action['cb']) > 0:
                options['action'] = action
            command.set(**options)
            bot.whisper(source.username, 'Volcania Updated the command (ID: {command.id})'.format(command=command))

    def remove_banphrase(bot, source, message, event, args):
        if message:
            id = None
            filter = None
            try:
                id = int(message)
            except Exception:
                pass

            if id is not None:
                filter = bot.filters.get(id=id)
            else:
                filter = bot.filters.get(phrase=message.lower())

            if filter is None:
                bot.whisper(source.username, 'Volcania No banphrase with the given parameters found')
                return False

            bot.whisper(source.username, 'Volcania Successfully removed banphrase with id {0}'.format(filter.id))
            bot.filters.remove_filter(filter)
        else:
            bot.whisper(source.username, 'Volcania Usage: !remove banphrase (BANPHRASE_ID)')
            return False

    def remove_win(bot, source, message, event, args):
        bot.kvi['br_wins'].dec()
        bot.me('Volcania {0} removed a BR win!'.format(source.username))
        log.debug('{0} removed a BR win!'.format(source.username))

    def add_alias(bot, source, message, event, args):
        """Dispatch method for adding aliases to already-existing commands.
        Usage: !add alias EXISTING_ALIAS NEW_ALIAS_1 NEW_ALIAS_2 ...
        """

        if message:
            message = message.replace('!', '')
            # Make sure we got both an existing alias and at least one new alias
            message_parts = message.split()
            if len(message_parts) < 2:
                bot.whisper(source.username, "Volcania Usage: !add alias existingalias newalias")
                return False

            existing_alias = message_parts[0]
            new_aliases = re.split('\|| ', ' '.join(message_parts[1:]))
            added_aliases = []
            already_used_aliases = []

            if existing_alias not in bot.commands:
                bot.whisper(source.username, 'Volcania No command called "{0}" found'.format(existing_alias))
                return False

            command = bot.commands[existing_alias]

            for alias in set(new_aliases):
                if alias in bot.commands:
                    already_used_aliases.append(alias)
                else:
                    added_aliases.append(alias)
                    bot.commands[alias] = command

            if len(added_aliases) > 0:
                command.command += '|' + '|'.join(added_aliases)
                bot.whisper(source.username, 'Volcania Successfully added the aliases {0} to {1}'.format(', '.join(added_aliases), existing_alias))
            if len(already_used_aliases) > 0:
                bot.whisper(source.username, 'Volcania The following aliases were already in use: {0}'.format(', '.join(already_used_aliases)))
        else:
            bot.whisper(source.username, "Volcania Usage: !add alias existingalias newalias")

    def remove_alias(bot, source, message, event, args):
        """Dispatch method for removing aliases from a command.
        Usage: !remove alias EXISTING_ALIAS_1 EXISTING_ALIAS_2"""
        if message:
            aliases = re.split('\|| ', message.lower())
            log.info(aliases)
            if len(aliases) < 1:
                bot.whisper(source.username, "Volcania Usage: !remove alias EXISTINGALIAS")
                return False

            num_removed = 0
            commands_not_found = []
            for alias in aliases:
                if alias not in bot.commands:
                    commands_not_found.append(alias)
                    continue

                command = bot.commands[alias]

                current_aliases = command.command.split('|')
                current_aliases.remove(alias)

                if len(current_aliases) == 0:
                    bot.whisper(source.username, "Volcania {0} is the only remaining alias for this command and can't be removed.".format(alias))
                    continue

                command.command = '|'.join(current_aliases)
                num_removed += 1
                del bot.commands[alias]

            whisper_str = ''
            if num_removed > 0:
                whisper_str = 'Volcania Successfully removed {0} aliases.'.format(num_removed)
            if len(commands_not_found) > 0:
                whisper_str += ' Aliases {0} not found'.format(', '.join(commands_not_found))
            if len(whisper_str) > 0:
                bot.whisper(source.username, whisper_str)
        else:
            bot.whisper(source.username, "Volcania Usage: !remove alias EXISTINGALIAS")

    def remove_command(bot, source, message, event, args):
        if message:
            id = None
            command = None
            try:
                id = int(message)
            except Exception:
                pass

            if id is None:
                potential_cmd = ''.join(message.split(' ')[:1]).lower().replace('!', '')
                if potential_cmd in bot.commands:
                    command = bot.commands[potential_cmd]
                    log.info('got command: {0}'.format(command))
            else:
                for key, check_command in bot.commands.items():
                    if check_command.id == id:
                        command = check_command
                        break

            if command is None:
                bot.whisper(source.username, 'Volcania No command with the given parameters found')
                return False

            if (not command.action.type == 'message' and source.level < 2000) or command.id == -1:
                bot.whisper(source.username, 'Volcania That command is not a normal command, it cannot be removed by you.')
                return False

            bot.whisper(source.username, 'Volcania Successfully removed command with id {0}'.format(command.id))
            bot.commands.remove_command(command)
        else:
            bot.whisper(source.username, 'Volcania Usage: !remove command (COMMAND_ID|COMMAND_ALIAS)')

    def add_link_blacklist(bot, source, message, event, args):
        parts = message.split(' ')
        try:
            if not parts[0].isnumeric():
                for link in parts:
                    bot.link_checker.blacklist_url(link)
            else:
                for link in parts[1:]:
                    bot.link_checker.blacklist_url(link, level=int(parts[0]))
        except:
            log.exception("Unhandled exception in add_link")
            bot.whisper(source.username, "Volcania Some error occurred white adding your links")

        bot.whisper(source.username, 'Volcania Successfully added your links')

    def add_link_whitelist(bot, source, message, event, args):
        parts = message.split(' ')

        try:
            for link in parts:
                bot.link_checker.whitelist_url(link)
        except:
            log.exception("Unhandled exception in add_link")
            bot.whisper(source.username, "Volcania Some error occurred white adding your links")

        bot.whisper(source.username, 'Volcania Successfully added your links')

    def remove_link_blacklist(bot, source, message, event, args):
        parts = message.split(' ')
        try:
            for link in parts:
                bot.link_checker.unlist_url(link, 'blacklist')
        except:
            log.exception("Unhandled exception in add_link")
            bot.whisper(source.username, "Volcania Some error occurred white adding your links")

        bot.whisper(source.username, 'Volcania Successfully removed your links')

    def remove_link_whitelist(bot, source, message, event, args):
        parts = message.split(' ')
        try:
            for link in parts:
                bot.link_checker.unlist_url(link, 'whitelist')
        except:
            log.exception("Unhandled exception in add_link")
            bot.whisper(source.username, "Volcania Some error occurred white adding your links")

        bot.whisper(source.username, 'Volcania Successfully removed your links')

    def debug_command(bot, source, message, event, args):
        if message and len(message) > 0:
            try:
                id = int(message)
            except Exception:
                id = -1

            command = False

            if id == -1:
                potential_cmd = ''.join(message.split(' ')[:1]).lower()
                if potential_cmd in bot.commands:
                    command = bot.commands[potential_cmd]
            else:
                for key, potential_cmd in bot.commands.items():
                    if potential_cmd.id == id:
                        command = potential_cmd
                        break

            if not command:
                bot.whisper(source.username, 'Volcania No command with found with the given parameters.')
                return False

            data = collections.OrderedDict()
            data['id'] = command.id
            data['level'] = command.level
            data['type'] = command.action.type if command.action is not None else 'func'
            data['cost'] = command.cost
            data['cd_all'] = command.delay_all
            data['cd_user'] = command.delay_user
            data['mod_only'] = command.mod_only

            if data['type'] == 'message':
                data['response'] = command.action.response
            elif data['type'] == 'func' or data['type'] == 'rawfunc':
                data['cb'] = command.action.cb.__name__

            bot.whisper(source.username, ', '.join(['%s=%s' % (key, value) for (key, value) in data.items()]))
        else:
            bot.whisper(source.username, 'Volcania Usage: !debug command (COMMAND_ID|COMMAND_ALIAS)')

    def debug_user(bot, source, message, event, args):
        if message and len(message) > 0:
            username = message.split(' ')[0].strip().lower()
            user = bot.users[username]

            if user.id == -1:
                del bot.users[username]
                bot.whisper(source.username, 'Volcania No user with this username found.')
                return False

            data = collections.OrderedDict()
            data['id'] = user.id
            data['level'] = user.level
            data['num_lines'] = user.num_lines
            data['points'] = user.points
            data['last_seen'] = user.last_seen
            data['last_active'] = user.last_active

            bot.whisper(source.username, ', '.join(['%s=%s' % (key, value) for (key, value) in data.items()]))
        else:
            bot.whisper(source.username, 'Volcania Usage: !debug user USERNAME')

    def level(bot, source, message, event, args):
        if message:
            msg_args = message.split(' ')
            if len(msg_args) > 1:
                username = msg_args[0].lower()
                new_level = int(msg_args[1])
                if new_level >= source.level:
                    bot.whisper(source.username, 'Volcania You cannot promote someone to the same or higher level as you ({0}).'.format(source.level))
                    return False

                user = bot.users.find(username)

                if not user:
                    bot.whisper(source.username, 'Volcania No user with that name found.')
                    return False

                user.level = new_level
                user.needs_sync = True

                bot.whisper(source.username, 'Volcania {0}\'s user level set to {1}'.format(username, new_level))

                return True

        bot.whisper(source.username, 'Volcania Usage: !level USERNAME NEW_LEVEL')
        return False

    def say(bot, source, message, event, args):
        if message:
            bot.say(message)

    def whisper(bot, source, message, event, args):
        if message:
            msg_args = message.split(' ')
            if len(msg_args) > 1:
                username = msg_args[0]
                rest = ' '.join(msg_args[1:])
                bot.whisper(username, rest)

    def top3(bot, source, message, event, args):
        """Prints out the top 3 chatters"""
        users = []
        for user in bot.users.db_session.query(User).order_by(desc(User.num_lines))[:3]:
            users.append('{user.username_raw} ({user.num_lines})'.format(user=user))

        bot.me('Volcania Top 3 lines: {0}'.format(', '.join(users)))

    def top3_month(bot, source, message, event, args):
        """Prints out the top 3 chatters this month"""
        users = []
        for user in bot.users.db_session.query(User).order_by(desc(User.num_lines_month))[:3]:
            users.append('{user.username_raw} ({user.num_lines_month})'.format(user=user))

        bot.me('Volcania Top 3 lines this month: {0} PogChamp'.format(', '.join(users)))
   
    def ban(bot, source, message, event, args):
        if message:
            username = message.split(' ')[0]
            log.debug('banning {0}'.format(username))
            bot.ban(username)

    def paid_timeout(bot, source, message, event, args):
        if 'time' in args:
            _time = int(args['time'])
        else:
            _time = 600

        if message:
            username = message.split(' ')[0]
            if len(username) < 2:
                return False

            victim = bot.users.find(username)
            if victim is None:
                bot.whisper(source.username, 'Volcania This user does not exist FailFish')
                return False

            """
            if victim == source:
                bot.whisper(source.username, 'Volcania You can\'t timeout yourself FailFish')
                return False
                """

            if victim.level >= 500:
                bot.whisper(source.username, 'Volcania This person has mod privileges, timeouting this person is not worth it.')
                return False

            now = datetime.datetime.now()
            if victim.timed_out is True and victim.timeout_end > now:
                victim.timeout_end += datetime.timedelta(seconds=_time)
                bot.whisper(victim.username, 'Volcania {victim.username}, you were timed out for an additional {time} seconds by {source.username}'.format(
                    victim=victim,
                    source=source,
                    time=_time))
                bot.whisper(source.username, 'Volcania You just used {0} points to time out {1} for an additional {2} seconds.'.format(args['command'].cost, username, _time))
                num_seconds = int((victim.timeout_end - now).total_seconds())
                bot._timeout(username, num_seconds)
            else:
                bot.whisper(source.username, 'Volcania You just used {0} points to time out {1} for {2} seconds.'.format(args['command'].cost, username, _time))
                bot.whisper(username, 'Volcania {0} just timed you out for {1} seconds. /w {2} !$unbanme to unban yourself for points'.format(source.username, _time, bot.nickname))
                bot._timeout(username, _time)
                victim.timed_out = True
                victim.timeout_start = now
                victim.timeout_end = now + datetime.timedelta(seconds=_time)
            payload = {'user': source.username, 'victim': victim.username}
            bot.websocket_manager.emit('timeout', payload)
            return True

        return False

    def set_game(bot, source, message, event, args):
        if message:
            bot.say('Volcania {0} updated the game to "{1}"'.format(source.username_raw, message))
            bot.twitchapi.set_game(bot.streamer, message)

    def ban_source(bot, source, message, event, args):
        if 'filter' in args and 'notify' in args:
            if args['notify'] == 1:
                bot.whisper(source.username, 'Volcania You have been permanently banned because your message matched our "{0}"-filter.'.format(args['filter'].name))

        log.debug('banning {0}'.format(source.username))
        bot.ban(source.username)

    def timeout_source(bot, source, message, event, args):
        if 'time' in args:
            _time = int(args['time'])
        else:
            _time = 600

        if 'filter' in args and 'notify' in args:
            if args['notify'] == 1:
                bot.whisper(source.username, 'Volcania You have been timed out for {0} seconds because your message matched our "{1}"-filter.'.format(_time, args['filter'].name))

        log.debug(args)

        log.debug('timeouting {0}'.format(source.username))
        bot.timeout(source.username, _time)

    def single_timeout_source(bot, source, message, event, args):
        if 'time' in args:
            _time = int(args['time'])
        else:
            _time = 600

        bot._timeout(source.username, _time)

    def set_deck(bot, source, message, event, args):
        """Dispatch method for setting the current deck.
        The command takes a link as its argument.
        If the link is an already-added deck, the deck should be set as the current deck
        and its last use date should be set to now.
        Usage: !setdeck imgur.com/abcdefgh"""

        if message:
            deck, new_deck = bot.decks.set_current_deck(message)
            if new_deck is True:
                bot.whisper(source.username, 'Volcania This deck is a new deck. Its ID is {deck.id}'.format(deck=deck))
            else:
                bot.whisper(source.username, 'Volcania Updated an already-existing deck. Its ID is {deck.id}'.format(deck=deck))
                bot.decks.commit()

            bot.say('Volcania Successfully updated the latest deck.')
            return True

        return False

    def update_deck(bot, source, message, event, args):
        """Dispatch method for updating a deck.
        By default this will update things for the current deck, but you can update
        any deck assuming you know its ID.
        Usage: !updatedeck --name Midrange Secret --class paladin
        """

        if message:
            options, response = bot.decks.parse_update_arguments(message)
            if options is False:
                bot.whisper(source.username, 'Volcania Invalid update deck command')
                return False

            if 'id' in options:
                deck = bot.decks.find(id=options['id'])
                # We remove id from options here so we can tell the user what
                # they have updated.
                del options['id']
            else:
                deck = bot.decks.current_deck

            if deck is None:
                bot.whisper(source.username, 'Volcania No valid deck to update.')
                return False

            if len(options) == 0:
                bot.whisper(source.username, 'Volcania You have given me nothing to update with the deck!')
                return False

            deck.set(**options)
            bot.decks.commit()
            bot.whisper(source.username, 'Volcania Updated deck with ID {deck.id}. Updated {list}'.format(deck=deck, list=', '.join([key for key in options])))

            return True
        else:
            bot.whisper(source.username, 'Volcania Usage example: !updatedeck --name Midrange Secret --class paladin')
            return False

    def remove_deck(bot, source, message, event, args):
        """Dispatch method for removing a deck.
        Usage: !removedeck imgur.com/abcdef
        OR
        !removedeck 123
        """

        if message:
            id = None
            try:
                id = int(message)
            except Exception:
                pass

            deck = bot.decks.find(id=id, link=message)

            if deck is None:
                bot.whisper(source.username, 'Volcania No deck matching your parameters found.')
                return False

            try:
                bot.decks.remove_deck(deck)
                bot.whisper(source.username, 'Volcania Successfully removed the deck.')
            except:
                log.exception('An exception occured while attempting to remove the deck')
                bot.whisper(source.username, 'Volcania An error occured while removing your deck.')
                return False
            return True
        else:
            bot.whisper(source.username, 'Volcania Usage example: !removedeck http://imgur.com/abc')
            return False

    def welcome_sub(bot, source, message, event, args):
        match = args['match']
        num_lines = bot.users[match.group(1)].num_lines
        bot.kvi['active_subs'].inc()

        phrase_data = {
                'username': match.group(1),
                'num_lines': num_lines
                }

        bot.say(bot.phrases['new_sub'].format(**phrase_data))
        bot.users[phrase_data['username']].subscriber = True

        payload = {'username': phrase_data['username']}
        bot.websocket_manager.emit('new_sub', payload)

    def resub(bot, source, message, event, args):
        match = args['match']
        num_lines = tyggbot.users[match.group(1)].num_lines
        phrase_data = {
                'username': match.group(1),
                'num_months': match.group(2),
                'num_lines' : num_lines
                }

        bot.say(bot.phrases['resub'].format(**phrase_data))
        bot.users[phrase_data['username']].subscriber = True
        if len(bot.newest_subs) >= 10:
            bot.newest_subs.pop(0)
        bot.newest_subs.append('{0}(Resub)'.format(match.group(1)))

        payload = {'username': phrase_data['username'], 'num_months': phrase_data['num_months']}
        bot.websocket_manager.emit('resub', payload)

    def sync_to(bot, source, message, event, args):
        log.debug('Calling sync_to from chat command...')
        bot.sync_to()

    def ignore(bot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = bot.users.find(tmp_username)

            if not user:
                bot.whisper(source.username, 'Volcania No user with that name found.')
                return False

            if user.ignored:
                bot.whisper(source.username, 'Volcania User is already ignored.')
                return False

            user.ignored = True
            user.needs_sync = True
            message = message.lower()
            bot.whisper(source.username, 'Volcania Now ignoring {0}'.format(user.username))

    def unignore(bot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = bot.users.find(tmp_username)

            if not user:
                bot.whisper(source.username, 'Volcania No user with that name found.')
                return False

            if user.ignored is False:
                bot.whisper(source.username, 'Volcania User is not ignored.')
                return False

            user.ignored = False
            user.needs_sync = True
            message = message.lower()
            bot.whisper(source.username, 'Volcania No longer ignoring {0}'.format(user.username))

    def permaban(bot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = bot.users.find(tmp_username)

            if not user:
                bot.whisper(source.username, 'Volcania No user with that name found.')
                return False

            if user.banned:
                bot.whisper(source.username, 'Volcania User is already permabanned.')
                return False

            user.banned = True
            user.needs_sync = True
            message = message.lower()
            bot.whisper(source.username, 'Volcania {0} has now been permabanned.'.format(user.username))

    def unpermaban(bot, source, message, event, args):
        if message:
            tmp_username = message.split(' ')[0].strip().lower()
            user = bot.users.find(tmp_username)

            if not user:
                bot.whisper(source.username, 'Volcania No user with that name found.')
                return False

            if user.banned is False:
                bot.whisper(source.username, 'Volcania User is not permabanned.')
                return False

            user.banned = False
            user.needs_sync = True
            message = message.lower()
            bot.whisper(source.username, 'Volcania {0} is no longer permabanned'.format(user.username))

    def tweet(bot, source, message, event, args):
        if message and len(message) > 1:
            try:
                log.info('sending tweet: {0}'.format(message[:140]))
                bot.twitter_manager.twitter_client.update_status(status=message)
            except Exception as e:
                log.error('Caught an exception: {0}'.format(e))

    def eval(bot, source, message, event, args):
        if bot.dev and message and len(message) > 0:
            try:
                exec(message)
            except:
                log.exception('Exception caught while trying to evaluate code: "{0}"'.format(message))
        else:
            log.error('Eval cannot be used like that.')

    def check_sub(bot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()
            user = bot.users.find(username)
        else:
            user = source

        if user:
            if user.subscriber:
                bot.say('Volcania {0} is a subscriber PogChamp'.format(user.username))
            else:
                bot.say('Volcania {0} is not a subscriber FeelsBadMan'.format(user.username))
        else:
            bot.say('Volcania {0} was not found in the user database'.format(username))

    def check_mod(bot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()
            user = bot.users.find(username)
        else:
            user = source

        if user:
            if user.moderator:
                bot.say('Volcania {0} is a moderator PogChamp'.format(user.username))
            else:
                bot.say('Volcania {0} is not a moderator FeelsBadMan (or has not typed in chat)'.format(user.username))
        else:
            bot.say('Volcania {0} was not found in the user database'.format(username))

    def last_seen(bot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()

            user = bot.users.find(username)
            if user:
                bot.say('Volcania {0}, {1} was last seen {2}, last active {3}'.format(source.username_raw, user.username, user.last_seen, user.last_active))
            else:
                bot.say('Volcania {0}, No user with that name found.'.format(source.username_raw))

    def points(bot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()
            user = bot.users.find(username)
        else:
            user = source

        if user:
            if user == source:
                bot.say('Volcania {0}, you have {1} points.'.format(source.username, user.points))
            else:
                bot.say('Volcania {0}, {1} has {2} points.'.format(source.username, user.username, user.points))
        else:
            return False

    def remindme(bot, source, message, event, args):
        if not message:
            return False

        parts = message.split(' ')
        if len(parts) < 2:
            # Not enough arguments
            return False

        delay = int(parts[0])
        extra_message = 'Volcania {0} {1}'.format(source.username, ' '.join(parts[1:]).strip())

        bot.execute_delayed(delay, bot.say, (extra_message, ))

    def ord(bot, source, message, event, args):
        if not message:
            return False

        try:
            ord_code = ord(message[0])
            bot.say(str(ord_code))
        except:
            return False

    def unban_source(bot, source, message, event, args):
        """Unban the user who ran the command."""
        bot.privmsg('.unban {0}'.format(source.username))
        bot.whisper(source.username, 'Volcania You have been unbanned.')
        source.timed_out = False

    def untimeout_source(bot, source, message, event, args):
        """Untimeout the user who ran the command.
        This is like unban except it will only remove timeouts, not permanent bans."""
        bot.privmsg('.timeout {0} 1'.format(source.username))
        bot.whisper(source.username, 'Volcania You have been unbanned.')
        source.timed_out = False

    def twitter_follow(bot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()
            if bot.twitter_manager.follow_user(username):
                bot.whisper(source.username, 'Volcania Now following {}'.format(username))
            else:
                bot.whisper(source.username, 'Volcania An error occured while attempting to follow {}, perhaps we are already following this person?'.format(username))

    def twitter_unfollow(bot, source, message, event, args):
        if message:
            username = message.split(' ')[0].strip().lower()
            if bot.twitter_manager.unfollow_user(username):
                bot.whisper('Volcania No longer following {}'.format(username))
            else:
                bot.whisper(source.username, 'Volcania An error occured while attempting to unfollow {}, perhaps we are not following this person?'.format(username))

    def reload(bot, source, message, event, args):
        if message and message in bot.reloadable:
            bot.reloadable[message].reload()
        else:
            bot.reload_all()

    def commit(bot, source, message, event, args):
        if message and message in bot.commitable:
            bot.commitable[message].commit()
        else:
            bot.commit_all()

    def add_highlight(bot, source, message, event, args):
        """Dispatch method for creating highlights
        Usage: !add highlight [options] DESCRIPTION
        Options available:
        --offset SECONDS
        """

        # Failsafe in case the user does not send a message
        message = message if message else ''

        options, description = bot.stream_manager.parse_highlight_arguments(message)

        if options is False:
            bot.whisper(source.username, 'Volcania Invalid highlight arguments.')
            return False

        if len(description) > 0:
            options['description'] = description

        if 'id' in options:
            id = options['id']
            del options['id']
            if len(options) > 0:
                res = bot.stream_manager.update_highlight(id, **options)

                if res is True:
                    bot.whisper(source.username, 'Volcania Successfully updated your highlight ({0})'.format(', '.join([key for key in options])))
                else:
                    bot.whisper(source.username, 'Volcania A highlight with this ID does not exist.')
            else:
                bot.whisper(source.username, 'Volcania Nothing to update! Give me some arguments')
        else:
            res = bot.stream_manager.create_highlight(**options)

            if res is True:
                bot.whisper(source.username, 'Volcania Successfully created your highlight')
            else:
                bot.whisper(source.username, 'Volcania An error occured while adding your highlight: {0}'.format(res))

            log.info('Create a highlight at the current timestamp!')

    def remove_highlight(bot, source, message, event, args):
        """Dispatch method for removing highlights
        Usage: !remove highlight HIGHLIGHT_ID
        """

        if message is None:
            bot.whisper(source.username, 'Volcania Usage: !remove highlight ID')
            return False

        try:
            id = int(message.split()[0])
        except ValueError:
            bot.whisper(source.username, 'Volcania Usage: !remove highlight ID')
            return False

        res = bot.stream_manager.remove_highlight(id)
        if res is True:
            bot.whisper(source.username, 'Volcania Successfully removed highlight with ID {}.'.format(id))
        else:
            bot.whisper(source.username, 'Volcania No highlight with the ID {} found.'.format(id))

    def follow_age(bot, source, message, event, args):
        username = source.username
        if message is not None and len(message) > 0:
            potential_user = bot.users.find(message.split(' ')[0])
            if potential_user is not None:
                username = potential_user.username

        bot.action_queue.add(check_follow_age, args=[bot, source, username])

    def initiate_duel(bot, source, message, event, args):
        """
        Initiate a duel with a user.
        You can also bet points on the winner.
        By default, the maximum amount of points you can spend is 420.
        You can increase this by changing the max_pot variable in extra_args.
        NOTE: Right now there's no way to easily change extra_args,
              you have to modify it in the database.

        How to add: !add funccommand duel initiate_duel --cd 0 --usercd 5
        How to use: !duel USERNAME POINTS_TO_BET
        """

        if message is None:
            return False

        max_pot = args.get('max_pot', 420)

        init_dueling_variables(source)

        msg_split = message.split()
        username = msg_split[0]
        user = bot.users.find(username)
        duel_price = 0
        if user is None:
            # No user was found with this username
            return False

        if len(msg_split) > 1:
            try:
                duel_price = int(msg_split[1])
                if duel_price < 0:
                    return False

                if duel_price > max_pot:
                    duel_price = max_pot
            except ValueError:
                pass

        if source.duel_target is not False:
            bot.whisper(source.username, 'Volcania You already have a duel request active with {}. Type !cancelduel to cancel your duel request.'.format(source.duel_target.username_raw))
            return False

        if user == source:
            # You cannot duel yourself
            return False

        if user.last_active is None or (datetime.datetime.now() - user._last_active).total_seconds() > 5 * 60:
            bot.whisper(source.username, 'Volcania This user has not been active in chat within the last 5 minutes. Get them to type in chat before sending another challenge')
            return False

        if user.points < duel_price or source.points < duel_price:
            bot.whisper(source.username, 'Volcania You or your target do not have more than {} points, therefore you cannot duel for that amount.'.format(duel_price))
            return False

        init_dueling_variables(user)

        if user.duel_request is False:
            user.duel_request = source
            source.duel_target = user
            user.duel_price = duel_price
            bot.whisper(user.username, 'Volcania You have been challenged to a duel by {} for {} points. You can either !accept or !deny this challenge.'.format(source.username_raw, duel_price))
            bot.whisper(source.username, 'Volcania You have challenged {} for {} points'.format(user.username_raw, duel_price))
        else:
            bot.whisper(source.username, 'Volcania This person is already being challenged by {}. Ask them to answer the offer by typing !deny or !accept'.format(user.duel_request.username_raw))

    def cancel_duel(bot, source, message, event, args):
        """
        Cancel any duel requests you've sent.

        How to add: !add funccomand cancelduel|duelcancel cancel_duel --cd 0 --usercd 10
        How to use: !cancelduel
        """

        init_dueling_variables(source)

        if source.duel_target is not False:
            bot.whisper(source.username, 'Volcania You have cancelled the duel vs {}'.format(source.duel_target.username_raw))
            source.duel_target.duel_request = False
            source.duel_target = False
            source.duel_request = False

    def accept_duel(bot, source, message, event, args):
        """
        Accepts any active duel requests you've received.

        How to add: !add funccommand accept accept_duel --cd 0 --usercd 0
        How to use: !accept
        """

        init_dueling_variables(source)
        duel_tax = 0.3  # 30% tax

        if source.duel_request is not False:
            if source.points < source.duel_price or source.duel_request.points < source.duel_price:
                bot.whisper(source.username, 'Volcania Your duel request with {} was cancelled due to one of you not having enough points.'.format(source.duel_request.username_raw))
                bot.whisper(source.duel_request.username, 'Volcania Your duel request with {} was cancelled due to one of you not having enough points.'.format(source.username_raw))
                source.duel_request = None
                return False
            source.points -= source.duel_price
            source.duel_request.points -= source.duel_price
            winning_pot = int(source.duel_price * (1.0 - duel_tax))
            participants = [source, source.duel_request]
            winner = random.choice(participants)
            participants.remove(winner)
            loser = participants.pop()
            winner.points += source.duel_price
            winner.points += winning_pot

            bot.duel_manager.user_won(winner, winning_pot)
            bot.duel_manager.user_lost(loser, source.duel_price)

            win_message = []
            win_message.append('Volcania {} won the duel vs {} PogChamp '.format(winner.username_raw, loser.username_raw))
            if source.duel_price > 0:
                win_message.append('Volcania The pot was {}, the winner gets his bet back + {} points'.format(source.duel_price, winning_pot))
            bot.say(*win_message)
            bot.websocket_manager.emit('notification', {'message': '{} won the duel vs {}'.format(winner.username_raw, loser.username_raw)})
            source.duel_request.duel_target = False
            source.duel_request = False
            source.duel_price = 0

    def decline_duel(bot, source, message, event, args):
        """
        Declines any active duel requests you've received.

        How to add: !add funccommand deny|decline decline_duel --cd 0 --usercd 0
        How to use: !decline
        """

        init_dueling_variables(source)

        if source.duel_request is not False:
            bot.whisper(source.username, 'Volcania You have declined the duel vs {}'.format(source.duel_request.username_raw))
            bot.whisper(source.duel_request.username, 'Volcania {} declined the duel challenge with you.'.format(source.username_raw))
            source.duel_request.duel_target = False
            source.duel_request = False

    def status_duel(bot, source, message, event, args):
        """
        Whispers you the current status of your active duel requests/duel targets

        How to add: !add funccommand duelstatus|statusduel status_duel --cd 0 --usercd 5
        How to use: !duelstatus
        """

        init_dueling_variables(source)

        msg = []
        if source.duel_request is not False:
            msg.append('Volcania You have a duel request by for {} points by {}'.format(source.duel_price, source.duel_request.username_raw))

        if source.duel_target is not False:
            msg.append('Volcania You have a duel request against for {} points by {}'.format(source.duel_target.duel_price, source.duel_target.username_raw))

        if len(msg) > 0:
            bot.whisper(source.username, '. '.join(msg))
        else:
            bot.whisper(source.username, 'Volcania You have no duel request or duel target. Type !duel USERNAME POT to duel someone!')

    def raffle(bot, source, message, event, args):
        if hasattr(Dispatch, 'raffle_running') and Dispatch.raffle_running is True:
            bot.say('Volcania {0}, a raffle is already running OMGScoots'.format(source.username_raw))
            return False

        Dispatch.raffle_users = []
        Dispatch.raffle_running = True
        Dispatch.raffle_points = 100

        try:
            if message is not None:
                Dispatch.raffle_points = int(message.split()[0])
        except ValueError:
            pass

        bot.websocket_manager.emit('notification', {'message': 'A raffle has been started!'})
        bot.execute_delayed(0.75, bot.websocket_manager.emit, ('notification', {'message': 'Type !join to enter!'}))

        bot.me('Volcania A raffle has begun for {} points. type !join to join the raffle! The raffle will end in 60 seconds'.format(Dispatch.raffle_points))
        bot.execute_delayed(15, bot.me, ('Volcania The raffle for {} points ends in 45 seconds! Type !join to join the raffle!'.format(Dispatch.raffle_points), ))
        bot.execute_delayed(30, bot.me, ('Volcania The raffle for {} points ends in 30 seconds! Type !join to join the raffle!'.format(Dispatch.raffle_points), ))
        bot.execute_delayed(45, bot.me, ('Volcania The raffle for {} points ends in 15 seconds! Type !join to join the raffle!'.format(Dispatch.raffle_points), ))

        bot.execute_delayed(60, Dispatch.end_raffle, (bot, source, message, event, args))

    def end_raffle(bot, source, message, event, args):
        if not Dispatch.raffle_running:
            return False

        Dispatch.raffle_running = False

        if len(Dispatch.raffle_users) == 0:
            bot.me('Volcania Wow, no one joined the raffle DansGame')
            return False

        winner = random.choice(Dispatch.raffle_users)

        Dispatch.raffle_users = []

        bot.websocket_manager.emit('notification', {'message': '{} won {} points in the raffle!'.format(winner.username_raw, Dispatch.raffle_points)})
        bot.me('Volcania The raffle has finished! {0} won {1} points! PogChamp'.format(winner.username_raw, Dispatch.raffle_points))

        winner.points += Dispatch.raffle_points
        winner.needs_sync = True

    def join(bot, source, message, event, args):
        if not Dispatch.raffle_running:
            return False

        for user in Dispatch.raffle_users:
            if user == source:
                return False

        # Added user to the raffle
        Dispatch.raffle_users.append(source)
