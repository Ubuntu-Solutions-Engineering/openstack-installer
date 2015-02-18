#!/usr/bin/env python3
#
# parse-image-config.py - Cloud installer image specifier munging
#
# Copyright 2014 Canonical, Ltd.
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

import os
import sys
import traceback
import yaml


DEFAULT_MIRROR_LIST = yaml.load("""[
{url: 'http://cloud-images.ubuntu.com/releases/',
name_prefix: 'ubuntu:released',
path: 'streams/v1/index.sjson', max: 1,
item_filters: ['release=trusty', 'arch~(x86_64|amd64)',
'ftype~(disk1.img|disk.img)']}]
""")


def main():

    releases = set()
    arches = set()
    try:
        for arg in sys.argv[2:]:
            type, val = arg.split('=')
            if type == "releases" and val:
                releases.update(val.split(','))
            elif type == "arches" and val:
                print(val.split(','))
                arches.update(val.split(','))

    except:
        raise Exception("Error splitting image specs")

    filter_args = ['ftype~(disk1.img|disk.img)']

    def getarg(argtype, argset):
        variants = "|".join(argset)
        argstr = "{}~({})".format(argtype, variants)
        return argstr

    if len(releases) > 0:
        filter_args.append(getarg("release", releases))
    else:
        filter_args.append("release=trusty")

    if len(arches) > 0:
        filter_args.append(getarg("arch", arches))
    else:
        filter_args.append("arch~(x86_64|amd64)")

    try:

        ml = DEFAULT_MIRROR_LIST
        ml[0]['item_filters'] = filter_args

        # default_flow_style=True is the most compact and best
        # survives the nested quoting:
        mls = yaml.dump(ml, default_flow_style=True)

        yaml_config['glance-simplestreams-sync']['mirror_list'] = mls

        with open(filename, 'w') as f:
            yaml.dump(yaml_config, stream=f, default_flow_style=False)

    except:
        raise Exception("Error modifying YAML config:"
                        " Original traceback follows:\n\n" +
                        traceback.format_exc())


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stderr.write("usage: {} arches=[arches]"
                         " releases=[releases]\n".format(sys.argv[0]))
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename) as f:
        yaml_config = yaml.load(f)

    os.rename(filename, filename + ".bak")

    try:
        main()
        os.unlink(filename + ".bak")
    except:
        sys.stderr.write("Error editing image specs:\n")
        sys.stderr.write(traceback.format_exc())
        os.rename(filename + ".bak", filename)
