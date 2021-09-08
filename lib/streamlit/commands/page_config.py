# Copyright 2018-2021 Streamlit Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import urllib.parse

from streamlit.report_thread import get_report_ctx
from streamlit.proto import ForwardMsg_pb2
from streamlit.proto import PageConfig_pb2
from streamlit.elements import image
from streamlit.errors import StreamlitAPIException


def set_page_config(
    page_title=None,
    page_icon=None,
    layout="centered",
    initial_sidebar_state="auto",
    menu_options=None,
):
    """
    Configures the default settings of the page.

    .. note::
        This must be the first Streamlit command used in your app, and must only
        be set once.

    Parameters
    ----------
    page_title: str or None
        The page title, shown in the browser tab. If None, defaults to the
        filename of the script ("app.py" would show "app • Streamlit").
    page_icon : Anything supported by st.image or str or None
        The page favicon.
        Besides the types supported by `st.image` (like URLs or numpy arrays),
        you can pass in an emoji as a string ("🦈") or a shortcode (":shark:").
        If you're feeling lucky, try "random" for a random emoji!
        Emoji icons are courtesy of Twemoji and loaded from MaxCDN.
    layout: "centered" or "wide"
        How the page content should be laid out. Defaults to "centered",
        which constrains the elements into a centered column of fixed width;
        "wide" uses the entire screen.
    initial_sidebar_state: "auto" or "expanded" or "collapsed"
        How the sidebar should start out. Defaults to "auto",
        which hides the sidebar on mobile-sized devices, and shows it otherwise.
        "expanded" shows the sidebar initially; "collapsed" hides it.
    menu_options: dict
        Dictionary should be a string that maps to another string (URL). The
        accepted strings are "Get Help", "Report a Bug", and "About".

    Example
    -------
    >>> st.set_page_config(
    ...     page_title="Ex-stream-ly Cool App",
    ...     page_icon="🧊",
    ...     layout="wide",
    ...     initial_sidebar_state="expanded",
    ...     menu_options={'Get Help': 'google.com',
    ...     'Report a bug': "google.com",
    ...     'About': "This is an extremely cool app!"}
    ... )
    """

    msg = ForwardMsg_pb2.ForwardMsg()

    if page_title:
        msg.page_config_changed.title = page_title

    if page_icon:
        if page_icon == "random":
            page_icon = get_random_emoji()

        msg.page_config_changed.favicon = image.image_to_url(
            page_icon,
            width=-1,  # Always use full width for favicons
            clamp=False,
            channels="RGB",
            output_format="JPEG",
            image_id="favicon",
            allow_emoji=True,
        )

    if layout == "centered":
        layout = PageConfig_pb2.PageConfig.CENTERED
    elif layout == "wide":
        layout = PageConfig_pb2.PageConfig.WIDE
    else:
        raise StreamlitAPIException(
            f'`layout` must be "centered" or "wide" (got "{layout}")'
        )
    msg.page_config_changed.layout = layout

    if initial_sidebar_state == "auto":
        initial_sidebar_state = PageConfig_pb2.PageConfig.AUTO
    elif initial_sidebar_state == "expanded":
        initial_sidebar_state = PageConfig_pb2.PageConfig.EXPANDED
    elif initial_sidebar_state == "collapsed":
        initial_sidebar_state = PageConfig_pb2.PageConfig.COLLAPSED
    else:
        raise StreamlitAPIException(
            '`initial_sidebar_state` must be "auto" or "expanded" or "collapsed" '
            + f'(got "{initial_sidebar_state}")'
        )

    msg.page_config_changed.initial_sidebar_state = initial_sidebar_state

    if menu_options is not None:
        lowercase_menu_options = {
            k.lower().strip(): v if v else "" for k, v in menu_options.items()
        }

        menu_options_proto = msg.page_config_changed.menu_options
        if "get help" in lowercase_menu_options:
            if lowercase_menu_options["get help"]:
                help_url = lowercase_menu_options["get help"]
                help_url = fix_url(help_url)
                menu_options_proto.get_help_url = help_url
            else:
                menu_options_proto.hide_get_help = True

        if "report a bug" in lowercase_menu_options:
            if lowercase_menu_options["report a bug"]:
                bug_url = lowercase_menu_options["report a bug"]
                bug_url = fix_url(bug_url)
                menu_options_proto.report_a_bug_url = bug_url
            else:
                menu_options_proto.hide_report_a_bug = True

        if "about" in lowercase_menu_options:
            menu_options_proto.about_section_md = lowercase_menu_options["about"]

    ctx = get_report_ctx()
    if ctx is None:
        return
    ctx.enqueue(msg)


def get_random_emoji():
    import random

    # Emojis recommended by https://share.streamlit.io/rensdimmendaal/emoji-recommender/main/app/streamlit.py
    # for the term "streamlit". Watch out for zero-width joiners,
    # as they won't parse correctly in the list() call!
    RANDOM_EMOJIS = list(
        "🔥™🎉🚀🌌💣✨🌙🎆🎇💥🤩🤙🌛🤘⬆💡🤪🥂⚡💨🌠🎊🍿😛🔮🤟🌃🍃🍾💫▪🌴🎈🎬🌀🎄😝☔⛽🍂💃😎🍸🎨🥳☀😍🅱🌞😻🌟😜💦💅🦄😋😉👻🍁🤤👯🌻‼🌈👌🎃💛😚🔫🙌👽🍬🌅☁🍷👭☕🌚💁👅🥰🍜😌🎥🕺❕🧡☄💕🍻✅🌸🚬🤓🍹®☺💪😙☘🤠✊🤗🍵🤞😂💯😏📻🎂💗💜🌊❣🌝😘💆🤑🌿🦋😈⛄🚿😊🌹🥴😽💋😭🖤🙆👐⚪💟☃🙈🍭💻🥀🚗🤧🍝💎💓🤝💄💖🔞⁉⏰🕊🎧☠♥🌳🏾🙉⭐💊🍳🌎🙊💸❤🔪😆🌾✈📚💀🏠✌🏃🌵🚨💂🤫🤭😗😄🍒👏🙃🖖💞😅🎅🍄🆓👉💩🔊🤷⌚👸😇🚮💏👳🏽💘💿💉👠🎼🎶🎤👗❄🔐🎵🤒🍰👓🏄🌲🎮🙂📈🚙📍😵🗣❗🌺🙄👄🚘🥺🌍🏡♦💍🌱👑👙☑👾🍩🥶📣🏼🤣☯👵🍫➡🎀😃✋🍞🙇😹🙏👼🐝⚫🎁🍪🔨🌼👆👀😳🌏📖👃🎸👧💇🔒💙😞⛅🏻🍴😼🗿🍗♠🦁✔🤖☮🐢🐎💤😀🍺😁😴📺☹😲👍🎭💚🍆🍋🔵🏁🔴🔔🧐👰☎🏆🤡🐠📲🙋📌🐬✍🔑📱💰🐱💧🎓🍕👟🐣👫🍑😸🍦👁🆗🎯📢🚶🦅🐧💢🏀🚫💑🐟🌽🏊🍟💝💲🐍🍥🐸☝♣👊⚓❌🐯🏈📰🌧👿🐳💷🐺📞🆒🍀🤐🚲🍔👹🙍🌷🙎🐥💵🔝📸⚠❓🎩✂🍼😑⬇⚾🍎💔🐔⚽💭🏌🐷🍍✖🍇📝🍊🐙👋🤔🥊🗽🐑🐘🐰💐🐴♀🐦🍓✏👂🏴👇🆘😡🏉👩💌😺✝🐼🐒🐶👺🖕👬🍉🐻🐾⬅⏬▶👮🍌♂🔸👶🐮👪⛳🐐🎾🐕👴🐨🐊🔹©🎣👦👣👨👈💬⭕📹📷"
    )

    # Also pick out some vanity emojis.
    ENG_EMOJIS = [
        "🎈",  # st.balloons 🎈🎈
        "🤓",  # Abhi
        "🏈",  # Amey
        "🚲",  # Thiago
        "🐧",  # Matteo
        "🦒",  # Ken
        "🐳",  # Karrie
        "🕹️",  # Jonathan
        "🇦🇲",  # Henrikh
        "🎸",  # Guido
        "🦈",  # Austin
        "💎",  # Emiliano
        "👩‍🎤",  # Naomi
        "🧙‍♂️",  # Jon
        "🐻",  # Brandon
        "🎎",  # James
        # TODO: Solicit emojis from the rest of Streamlit
    ]

    # Weigh our emojis 10x, cuz we're awesome!
    # TODO: fix the random seed with a hash of the user's app code, for stability?
    return random.choice(RANDOM_EMOJIS + 10 * ENG_EMOJIS)

def fix_url(url):
    p = urllib.parse.urlparse(url, "http")
    netloc = p.netloc or p.path
    path = p.path if p.netloc else ""
    if not netloc.startswith("www."):
        netloc = "www." + netloc

    p = urllib.parse.ParseResult("http", netloc, path, *p[3:])
    return p.geturl()
