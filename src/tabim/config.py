import enum

import attr


class LyricsPosition(str, enum.Enum):
    Top = "top"
    Bottom = "bottom"


@attr.s(auto_attribs=True, slots=True)
class HeaderConfig:
    show_title: bool = True
    center_title: bool = True
    show_subtitle: bool = True
    show_artist: bool = True
    show_album: bool = True
    show_music: bool = True
    show_words: bool = True
    show_tab: bool = True
    show_copyright: bool = True


@attr.s(auto_attribs=True, slots=True)
class LineConfig:
    line_length: int = 60
    show_lyrics: bool = True
    show_bar_numbers: bool = True
    lyrics_position: LyricsPosition = LyricsPosition.Top


@attr.s(auto_attribs=True, slots=True)
class RenderConfig:
    header: HeaderConfig = attr.Factory(HeaderConfig)
    line: LineConfig = attr.Factory(LineConfig)
