# Copyright 2015 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Palette Loader """


def apply_default_colors(cls):
    color_map = {'orange': '#f60',
                 'light_orange': '#f80',
                 'dark_magenta': '#608',
                 'light_magenta': '#f0f',
                 'light_red': '#f00',
                 'light_green': '#0d0',
                 'white': 'white',
                 'black': 'black',
                 'light_gray': 'g82',
                 'cool_gray': 'g50',
                 'warm_gray': 'g15',
                 'blue': '#08f',
                 'dark_blue': '#00f'}
    for k, v in color_map.items():
        setattr(cls, k, v)
    return cls


@apply_default_colors
class Palette:
    pass

STYLES = [
    ('frame_header', '', '', '',
     Palette.white, Palette.orange),
    ('frame_subheader', '', '', '',
     Palette.white, Palette.warm_gray),
    ('frame_excerpt', '', '', '',
     Palette.cool_gray, ''),
    ('frame_footer', '', '', '',
     Palette.white, Palette.warm_gray),
    ('body', '', '', '',
     Palette.white, ''),
    ('button_primary', '', '',
     '', Palette.white, Palette.cool_gray),
    ('button_primary focus', '', '', '',
     Palette.white, Palette.light_orange),
    ('button_secondary', '', '', '',
     Palette.white, Palette.cool_gray),
    ('button_secondary focus', '', '', '',
     Palette.white, Palette.light_orange),
    ('info_minor', '', '', '',
     Palette.warm_gray, ''),
    ('info_major', '', '', '',
     Palette.light_green, ''),
    ('error_major', '', '', '',
     Palette.light_red, ''),
    ('status_info', '', '', '',
     Palette.light_green, Palette.warm_gray),
    ('status_error', '', '', '',
     Palette.light_red, Palette.warm_gray),
    ('string_input', '', '', '',
     Palette.white, Palette.cool_gray),
    ('string_input focus', '', '', '',
     Palette.white, Palette.orange),
    ('dialog', '', '', '',
     Palette.white, Palette.warm_gray),
    ('radio_input', '', '', '',
     Palette.white, Palette.warm_gray),
    ('radio_input focus', '', '', '',
     Palette.orange, Palette.warm_gray),
    ('header_title', '', '', '',
     Palette.orange, ''),
    ('pending_icon_on', '', '', '',
     Palette.blue, ''),
    ('pending_icon', '', '', '',
     Palette.blue, ''),
    ('error_icon', '', '', '',
     Palette.light_red, ''),
    ('success_icon', '', '', '',
     Palette.light_green, ''),
    ('column_header', '', '', '',
     Palette.white, Palette.blue),


    # TODO: Update colors
    ('deploy_highlight_start', 'dark gray', 'light green'),
    ('deploy_highlight_end', 'dark gray', 'dark green'),
    ('disabled_button', 'black', 'white'),
    ('disabled_button_focus', 'black', 'light gray'),
    ('divider_line', 'light gray', 'default'),
    ('filter', 'dark gray,underline', 'white'),
    ('filter_focus', 'dark gray,underline', 'light gray'),
    ('focus', 'white', 'dark gray'),
    ('radio focus', 'white,bold', 'dark magenta'),
    ('status_extra', 'light gray,bold', 'dark gray'),
    ('error', 'white', 'dark red'),
    ('info', 'light green', 'default'),
    ('label', 'dark gray', 'default'),
]
