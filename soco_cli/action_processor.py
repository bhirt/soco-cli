import os
import sys
import soco
import pprint
from collections import namedtuple

from . import sonos

pp = pprint.PrettyPrinter(width=120)


def error_and_exit(msg):
    # Print to stderror
    print("Error:", msg, file=sys.stderr)
    # Use os._exit() to avoid the catch-all 'except'
    os._exit(1)


def parameter_type_error(action, required_params):
    msg = "Action '{}' takes parameter(s): {}".format(action, required_params)
    error_and_exit(msg)


def parameter_number_error(action, parameter_number):
    msg = "Action '{}' takes {} parameter(s)".format(action, parameter_number)
    error_and_exit(msg)


# Action processing functions
def on_off_action(speaker, action, args, soco_function, use_local_speaker_list):
    """Method to deal with actions that have 'on|off semantics"""
    np = len(args)
    if action == "group_mute":
        speaker = speaker.group
        soco_function = "mute"
    if np == 0:
        state = "on" if getattr(speaker, soco_function) else "off"
        print(state)
    elif np == 1:
        arg = args[0].lower()
        if arg == "on":
            setattr(speaker, soco_function, True)
        elif arg == "off":
            setattr(speaker, soco_function, False)
        else:
            parameter_type_error(action, "on|off")
    else:
        parameter_number_error(action, "0 or 1")
    return True


def no_args_no_output(speaker, action, args, soco_function, use_local_speaker_list):
    if len(args) != 0:
        parameter_number_error(action, "no")
        return False
    getattr(speaker, soco_function)()
    return True


def no_args_one_output(speaker, action, args, soco_function, use_local_speaker_list):
    if len(args) != 0:
        parameter_number_error(action, "no")
        return False
    result = getattr(speaker, soco_function)
    if callable(result):
        print(getattr(speaker, soco_function)())
    else:
        print(result)
    return True


def list_queue(speaker, action, args, soco_function, use_local_speaker_list):
    if len(args) == 0:
        queue = speaker.get_queue(max_items=1000)
        for i in range(len(queue)):
            try:
                artist = queue[i].creator
            except:
                artist = ""
            try:
                album = queue[i].album
            except:
                album = ""
            try:
                title = queue[i].title
            except:
                title = ""
            print(
                "{:3d}: Artist: {} | Album: {} | Title: {}".format(
                    i + 1, artist, album, title
                )
            )
        return True
    else:
        parameter_number_error(action, "no")
        # Probably doesn't get here, but just in case
        return True


def list_numbered_things(speaker, action, args, sonos_function, use_local_speaker_list):
    if len(args) == 0:
        if sonos_function == "get_sonos_favorites":
            things = getattr(speaker.music_library, sonos_function)()
        else:
            things = getattr(speaker, sonos_function)()
        things_list = []
        for thing in things:
            things_list.append(thing.title)
        things_list.sort()
        index = 0
        for thing in things_list:
            index += 1
            print("{:3d}: {}".format(index, thing))
        return True
    else:
        parameter_number_error(action, "no")
        # Probably doesn't get here, but just in case
        return True


def volume_actions(speaker, action, args, sonos_function, use_local_speaker_list):
    np = len(args)
    # Special case for ramp_to_volume
    if sonos_function == "ramp_to_volume":
        if np == 1:
            vol = int(args[0])
            if 0 <= vol <= 100:
                print(speaker.ramp_to_volume(vol))
                return True
            else:
                parameter_type_error(action, "0 to 100")
                return False
        else:
            parameter_number_error(action, "1")
            return False
    if sonos_function == "group_volume":
        speaker = speaker.group
    if np == 0:
        print(speaker.volume)
    elif np == 1:
        try:
            vol = int(args[0])
        except:
            parameter_type_error(action, "integer from 0 to 100")
            return False
        if 0 <= vol <= 100:
            speaker.volume = vol
        else:
            parameter_type_error(action, "0 to 100")
            return False
    else:
        parameter_number_error(action, "0 or 1")
        return False
    return True


def relative_volume_actions(speaker, action, args, sonos_function, use_local_speaker_list):
    if len(args) != 1:
        parameter_number_error(action, "1")
        return False
    if sonos_function == "group_relative_volume":
        speaker = speaker.group
    try:
        vol = int(args[0])
    except:
        parameter_type_error(action, "integer from -100 to 100")
    if -100 <= vol <= 100:
        speaker.volume += vol
    else:
        parameter_type_error(action, "integer from -100 to 100")
        return False
    return True


def print_info(speaker, action, args, sonos_function, use_local_speaker_list):
    if len(args) > 0:
        parameter_number_error(action, "no")
        return False
    output = getattr(speaker, sonos_function)()
    for item in sorted(output):
        if item not in ["metadata", "uri"]:
            print("  {}: {}".format(item, output[item]))
    return True


def playback_mode(speaker, action, args, sonos_function, use_local_speaker_list):
    np = len(args)
    possible_args = [
            "normal",
            "repeat_all",
            "repeat_one",
            "shuffle",
            "shuffle_norepeat",
    ]
    if np == 0:
        print(speaker.play_mode)
    elif np == 1:
        if args[0].lower() in possible_args:
            speaker.play_mode = args[0]
        else:
            parameter_type_error(action, possible_args)
    else:
        parameter_number_error(action, "0 or 1")
        return False
    return True


def transport_state(speaker, action, args, sonos_function, use_local_speaker_list):
    if len(args) == 0:
        print(speaker.get_current_transport_info()["current_transport_state"])
        return True
    else:
        parameter_number_error(action, "no")
        return False


def play_favourite(speaker, action, args, sonos_function, use_local_speaker_list):
        if len(args) != 1:
            parameter_number_error(action, "1")
            return False
        favourite = args[0].lower()
        fs = speaker.music_library.get_sonos_favorites()
        the_fav = None
        # Strict match (case insensitive)
        for f in fs:
            if favourite == f.title.lower():
                the_fav = f
        # Loose substring match if strict match not available
        if not the_fav:
            for f in fs:
                if favourite in f.title.lower():
                    the_fav = f
        if the_fav:
            # play_uri works for some favourites
            try:
                uri = the_fav.get_uri()
                metadata = the_fav.resource_meta_data
                speaker.play_uri(uri=uri, meta=metadata)
                return True  # Success
            except Exception as e:
                e1 = e
                pass
            # Other favourites have to be added to the queue, then played
            try:
                # speaker.clear_queue()
                index = speaker.add_to_queue(the_fav)
                speaker.play_from_queue(index, start=True)
                return True
            except Exception as e2:
                error_and_exit("{}, {}".format(str(e1), str(e2)))
                return False
        error_and_exit("Favourite '{}' not found".format(favourite))
        return False


def play_uri(speaker, action, args, sonos_function, use_local_speaker_list):
    np = len(args)
    if not (np == 1 or np == 2):
        parameter_number_error(action, "1 or 2")
        return False
    else:
        force_radio = True if args[0][:4].lower() == "http" else False
        if np == 2:
            speaker.play_uri(
                args[0], title=args[1], force_radio=force_radio,
            )
        else:
            speaker.play_uri(args[0], force_radio=force_radio)
    return True


def sleep_timer(speaker, action, args, sonos_function, use_local_speaker_list):
    np = len(args)
    if np == 0:
        st = speaker.get_sleep_timer()
        if st:
            print(st)
        else:
            print(0)
    elif np == 1:
        try:
            t = int(args[0])
            if not 0 <= t <= 86399:
                raise Exception
        except:
            parameter_type_error(action, "integer > 0")
            return False
        speaker.set_sleep_timer(int(args[0]))
    else:
        parameter_number_error(action, "0 or 1")
        return False
    return True


def group(speaker, action, args, sonos_function, use_local_speaker_list):
    if len(args) != 1:
        parameter_number_error(action, "1")
        return False
    speaker2 = sonos.get_speaker(args[0], use_local_speaker_list)
    speaker.join(speaker2)
    return True


def operate_on_all(speaker, action, args, sonos_function, use_local_speaker_list):
    if len(args) != 0:
        parameter_number_error(action, "no")
        return False
    zones = speaker.all_zones
    for zone in zones:
        if zone.is_visible:
            try:
                # zone.unjoin()
                getattr(zone, sonos_function)()
            except:
                # Ignore errors here; don't want to halt on
                # a failed pause (e.g., if speaker isn't playing)
                continue
    return True


def zones(speaker, action, args, sonos_function, use_local_speaker_list):
    if len(args) != 0:
        parameter_number_error(action, "no")
        return False
    zones = speaker.all_zones if "all" in action else speaker.visible_zones
    for zone in zones:
        print("{} ({})".format(zone.player_name, zone.ip_address))
    return True


def play_from_queue(speaker, action, args, sonos_function, use_local_speaker_list):
    np = len(args)
    if np == 0:
        speaker.play_from_queue(0)
    elif np == 1:
        try:
            index = int(args[0])
        except:
            parameter_type_error(action, "integer")
            return False
        if 1 <= index <= speaker.queue_size:
            speaker.play_from_queue(index - 1)
        else:
            error_and_exit("Queue index '{}' is out of range".format(index))
            return False
    else:
        parameter_number_error(action, "0 or 1")
        return False
    return True


def remove_from_queue(speaker, action, args, sonos_function, use_local_speaker_list):
    if len(args) != 1:
        parameter_number_error(action, "1")
        return False
    try:
        index = int(args[0])
    except:
        parameter_type_error(action, "integer")
        return False
    qs = speaker.queue_size
    if 1 <= index <= qs:
        speaker.play_from_queue(index - 1)
    else:
        error_and_exit("Queue index should be between 1 and {}".format(qs))
        return False
    return True


def save_queue(speaker, action, args, sonos_function, use_local_speaker_list):
    if len(args) != 1:
        parameter_number_error(action, "1")
        return False
    speaker.create_sonos_playlist_from_queue(args[0])
    return True


def seek(speaker, action, args, sonos_function, use_local_speaker_list):
    if len(args) != 1:
        parameter_number_error(action, "1")
        return False
    try:
        speaker.seek(args[0])
    except:
        parameter_type_error(action, "HH:MM:SS on a seekable source")
        return False
    return True

def add_playlist_to_queue(speaker, action, args, sonos_function, use_local_speaker_list):
    if len(args) != 1:
        parameter_number_error(action, "1")
        return False
    name = args[0].lower()
    playlists = speaker.get_sonos_playlists()
    # Strict match
    for playlist in playlists:
        if name == playlist.title.lower():
            speaker.add_to_queue(playlist)
            return True
    # Fuzzy match
    for playlist in playlists:
        if name in playlist.title.lower():
            speaker.add_to_queue(playlist)
            return True
    error_and_exit("Playlist {} not found".format(args[0]))
    return False


def line_in(speaker, action, args, sonos_function, use_local_speaker_list):
    np = len(args)
    if not 0 <= np <= 2:
        parameter_number_error(action, "0, 1 or 2")
    if np == 0:
        state = "on" if speaker.is_playing_line_in else "off"
        print(state)
    elif np == 1 or np == 2:
        if args[0].lower() == "on":
            if np == 1:
                speaker.switch_to_line_in()
            elif np == 2:
                line_in_source = sonos.get_speaker(args[1], use_local_speaker_list)
                if not line_in_source:
                    error_and_exit("Speaker {} not found".format(args[1]))
                    return False
                speaker.switch_to_line_in(line_in_source)
        else:
            parameter_type_error(action, "'on' as first parameter")
    return True


def eq(speaker, action, args, sonos_function, use_local_speaker_list):
    np = len(args)
    if np > 1:
        parameter_number_error(action, "0 or 1")
        return False
    if np == 0:
        print(getattr(speaker, sonos_function))
    elif np == 1:
        try:
            setting = int(args[0])
        except:
            parameter_type_error(action, "integer from -10 to 10")
            return False
        if -10 <= setting <= 10:
            setattr(speaker, sonos_function, setting)
        else:
            parameter_type_error(action, "integer from -10 to 10")
            return False
    return True


def balance(speaker, action, args, sonos_function, use_local_speaker_list):
    np = len(args)
    if np > 1:
        parameter_number_error(action, "0 or 1")
        return False
    if np == 0:
        left, right = getattr(speaker, sonos_function)
        # Convert to something more intelligible
        print(right - left)
    elif np == 1:
        try:
            setting = int(args[0])
        except:
            parameter_type_error(action, "integer from -100 to 100")
            return False
        if -100 <= setting <= 100:
            left = 0 - setting
            right = 0 + setting
            setattr(speaker, sonos_function, (left, right))
        else:
            parameter_type_error(action, "integer from -100 to 100")
            return False
    return True


def process_action(speaker, action, args, use_local_speaker_list):
    sonos_function = actions.get(action, None)
    if sonos_function:
        return sonos_function.processing_function(
            speaker,
            action,
            args,
            sonos_function.soco_function,
            use_local_speaker_list,
        )
    else:
        return False


# Type for holding action processing functions
SonosFunction = namedtuple(
    "SonosFunction",
    ["processing_function", "soco_function",],
    rename=False,
)

# Actions and associated processing functions
actions = {
    "mute": SonosFunction(on_off_action, "mute"),
    "cross_fade": SonosFunction(on_off_action, "cross_fade"),
    "loudness": SonosFunction(on_off_action, "loudness"),
    "status_light": SonosFunction(on_off_action, "status_light"),
    "light": SonosFunction(on_off_action, "status_light"),
    "night_mode": SonosFunction(on_off_action, "night_mode"),
    "night": SonosFunction(on_off_action, "night_mode"),
    "dialog_mode": SonosFunction(on_off_action, "dialog_mode"),
    "dialog": SonosFunction(on_off_action, "dialog_mode"),
    "dialogue_mode": SonosFunction(on_off_action, "dialog_mode"),
    "dialogue": SonosFunction(on_off_action, "dialog_mode"),
    "play": SonosFunction(no_args_no_output, "play"),
    "stop": SonosFunction(no_args_no_output, "stop"),
    "pause": SonosFunction(no_args_no_output, "pause"),
    "next": SonosFunction(no_args_no_output, "next"),
    "previous": SonosFunction(no_args_no_output, "previous"),
    "prev": SonosFunction(no_args_no_output, "previous"),
    "list_queue": SonosFunction(list_queue, "get_queue"),
    "lq": SonosFunction(list_queue, "get_queue"),
    "queue": SonosFunction(list_queue, "get_queue"),
    "q": SonosFunction(list_queue, "get_queue"),
    "list_playlists": SonosFunction(list_numbered_things, "get_sonos_playlists"),
    "playlists": SonosFunction(list_numbered_things, "get_sonos_playlists"),
    "lp": SonosFunction(list_numbered_things, "get_sonos_playlists"),
    "list_favourites": SonosFunction(list_numbered_things, "get_sonos_favorites"),
    "list_favorites": SonosFunction(list_numbered_things, "get_sonos_favorites"),
    "list_favs": SonosFunction(list_numbered_things, "get_sonos_favorites"),
    "lf": SonosFunction(list_numbered_things, "get_sonos_favorites"),
    "volume": SonosFunction(volume_actions, "volume"),
    "vol": SonosFunction(volume_actions, "volume"),
    "v": SonosFunction(volume_actions, "volume"),
    "group_volume": SonosFunction(volume_actions, "group_volume"),
    "group_vol": SonosFunction(volume_actions, "group_volume"),
    "gv": SonosFunction(volume_actions, "group_volume"),
    "ramp_to_volume": SonosFunction(volume_actions, "ramp_to_volume"),
    "ramp": SonosFunction(volume_actions, "ramp_to_volume"),
    "relative_volume": SonosFunction(relative_volume_actions, "relative_volume"),
    "rel_vol": SonosFunction(relative_volume_actions, "relative_volume"),
    "rv": SonosFunction(relative_volume_actions, "relative_volume"),
    "group_relative_volume": SonosFunction(relative_volume_actions, "group_relative_volume"),
    "group_rel_vol": SonosFunction(relative_volume_actions, "group_relative_volume"),
    "grv": SonosFunction(relative_volume_actions, "group_relative_volume"),
    "track": SonosFunction(print_info, "get_current_track_info"),
    "play_mode": SonosFunction(playback_mode, "play_mode"),
    "mode": SonosFunction(playback_mode, "play_mode"),
    "playback_state": SonosFunction(transport_state, "get_current_transport_info"),
    "playback": SonosFunction(transport_state, "get_current_transport_info"),
    "state": SonosFunction(transport_state, "get_current_transport_info"),
    "favourite": SonosFunction(play_favourite, "play_favorite"),
    "favorite": SonosFunction(play_favourite, "play_favorite"),
    "play_fav": SonosFunction(play_favourite, "play_favorite"),
    "fav": SonosFunction(play_favourite, "play_favorite"),
    "pf": SonosFunction(play_favourite, "play_favorite"),
    "play_uri": SonosFunction(play_uri, "play_uri"),
    "uri": SonosFunction(play_uri, "play_uri"),
    "pu": SonosFunction(play_uri, "play_uri"),
    "sleep_timer": SonosFunction(sleep_timer, "sleep_timer"),
    "sleep": SonosFunction(sleep_timer, "sleep_timer"),
    "group": SonosFunction(group, "join"),
    "g": SonosFunction(group, "join"),
    "ungroup": SonosFunction(no_args_no_output, "unjoin"),
    "u": SonosFunction(no_args_no_output, "unjoin"),
    "party_mode": SonosFunction(no_args_no_output, "partymode"),
    "party": SonosFunction(no_args_no_output, "partymode"),
    "ungroup_all": SonosFunction(operate_on_all, "unjoin"),
    "zones": SonosFunction(zones, "zones"),
    "all_zones": SonosFunction(zones, "zones"),
    "rooms": SonosFunction(zones, "zones"),
    "all_rooms": SonosFunction(zones, "zones"),
    "visible_zones": SonosFunction(zones, "zones"),
    "visible_rooms": SonosFunction(zones, "zones"),
    "play_from_queue": SonosFunction(play_from_queue, "play_from_queue"),
    "play_queue": SonosFunction(play_from_queue, "play_from_queue"),
    "pfq": SonosFunction(play_from_queue, "play_from_queue"),
    "pq": SonosFunction(play_from_queue, "play_from_queue"),
    "remove_from_queue": SonosFunction(remove_from_queue, "remove_from_queue"),
    "rq": SonosFunction(remove_from_queue, "remove_from_queue"),
    "clear_queue": SonosFunction(no_args_no_output, "clear_queue"),
    "cq": SonosFunction(no_args_no_output, "clear_queue"),
    "group_mute": SonosFunction(on_off_action, "group_mute"),
    "save_queue": SonosFunction(save_queue, "create_sonos_playlist_from_queue"),
    "sq": SonosFunction(save_queue, "create_sonos_playlist_from_queue"),
    "queue_length": SonosFunction(no_args_one_output, "queue_size"),
    "add_playlist_to_queue": SonosFunction(add_playlist_to_queue, "add_to_queue"),
    "add_pl_to_queue": SonosFunction(add_playlist_to_queue, "add_to_queue"),
    "apq": SonosFunction(add_playlist_to_queue, "add_to_queue"),
    "pause_all": SonosFunction(operate_on_all, "pause"),
    "seek": SonosFunction(seek, "seek"),
    "line_in": SonosFunction(line_in, ""),
    "bass": SonosFunction(eq, "bass"),
    "treble": SonosFunction(eq, "treble"),
    "balance": SonosFunction(balance, "balance"),
}