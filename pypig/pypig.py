#!python3
"""
    Command line utility for managing private pypiserver.
    https://github.com/pypiserver/pypiserver

    Install with `pip install -e .`

    print help: `pypig -h`

    for individual commands: pypig <command> -h

    For frequent use store credentials in `~/.config/pypig/auth.json` as 

        {
            "index": "https://<repository-url>.com/",
            "username": "u",
            "password": "p"
        }
        
    These are treated as default values and overriden by flags, save any number of these.

    Example usage
    -------------

    List all packages

        pypig list

    List all instances of one package

        pypig list pytket

    Filter further (version range and platform)

        pypig list pytket --version 0.5.2 0.5.4 --platform linux

    Download packages - same filtering interface as list, but with optional directory

        pypig download -d downloads pytket --pyver 3.8

    Delete packages on server: Use with care!

        pypig remove pytket-qiskit 0.4.1
"""

import argparse
from typing import Sequence
import subprocess
import sys
from pathlib import Path
import json
import requests


class Package:
    def __init__(self, name, version, python_tag, abi_tag, platform, filetype):
        self.name = name
        self.version = version
        self.platform = platform
        self.python = python_tag
        self.abi = abi_tag
        self.type = filetype

    def __str__(self):
        return (
            " ".join(
                (
                    self.name,
                    self.version,
                    self.python,
                    self.abi,
                    self.platform,
                    self.type,
                )
            )
            + "\n"
        )

    def __repr__(self):
        return str(self)


class WheelPackage(Package):
    def __init__(self, filename):
        tags = tuple(s[::-1] for s in filename[::-1].split("-", maxsplit=4))[::-1]
        super().__init__(*tuple(tags + ("wheel",)))


class SourcePackage(Package):
    def __init__(self, filename):
        tags = [s[::-1] for s in filename[::-1].split("-", maxsplit=1)][::-1]
        super().__init__(tags[0], tags[1], "py3", "none", "any", "sdist")


def remove(args):
    response = requests.post(
        args.url,
        data={":action": "remove_pkg", "name": args.name, "version": args.version,},
        timeout=(args.timeout, args.timeout),
    )

    print(response)
    print(response.content)


def print_package_list(packages: Sequence[Package]):
    if not packages:
        print("No packages found matching filters")
        sys.exit(1)
    attrs = ("name", "version", "python", "platform", "type")
    cell_format = "{:>{width}}"

    titlepackage = Package("name", "version", "python", "abi", "platform", "type")
    sepackage = Package(*(["=" * max(len(x) for x in attrs)] * 6))
    packages = [titlepackage, sepackage] + list(packages)
    widths = [max(len(getattr(pack, attr)) for pack in packages) for attr in attrs]
    rows = (
        " ".join(
            cell_format.format(getattr(pack, attr), width=wid)
            for attr, wid in zip(attrs, widths)
        )
        for pack in packages
    )

    print("\n".join(rows))


def get_filtered_packages(args):

    if args.debug:
        with open(args.debug, "r") as f:
            readlines = f.readlines()
    else:
        response = requests.get(args.url + "/packages", data={}, timeout=args.timeout)
        readlines = response.text.splitlines()

    lines = (l.strip() for l in readlines)
    lines = (l[l.find(">") + 1 :] for l in lines if l.startswith("<a href"))
    lines = (l[: l.find("<")] for l in lines)

    extensions = {".whl": WheelPackage, ".tar.gz": SourcePackage}
    packages = (
        extensions[ex](l[: -len(ex)])
        for l in lines
        for ex in extensions
        if l.endswith(ex)
    )

    pyver_convert = lambda x: "cp{}{}".format(*x.split("."))

    if args.name:
        packages = filter(lambda x: x.name == args.name, packages)
    if args.version:
        vers = len(args.version)
        version_filter = lambda x: (
            (x.version == args.version[0])
            if vers == 1
            else (args.version[0] <= x.version <= args.version[1])
        )
        packages = filter(version_filter, packages)

    if args.pyver:
        cpver = pyver_convert(args.pyver)
        packages = filter(lambda x: x.python == cpver, packages)
    if args.platform:
        packages = filter(
            lambda x: args.platform in x.platform or x.platform == "any", packages
        )

    return list(packages)


def package_list(args):

    packages = get_filtered_packages(args)
    print_package_list(list(packages))


def download(args):
    packages = get_filtered_packages(args)

    base_sys_call = [
        sys.executable,
        "-m",
        "pip",
        "--default-timeout",
        str(args.timeout),
        "download",
        "--no-deps",
        "--pre",
        "-i",
        args.url,
    ]

    for package in packages:
        print(f"Downloading package {package}")
        sys_call = base_sys_call + [
            f"{package.name}=={package.version}",
            "-d",
            args.dest,
        ]

        if package.python.startswith("cp"):
            sys_call += [
                "--python",
                package.python[len("cp") :],
            ]
        if package.platform != "any":
            sys_call += [
                "--platform",
                package.platform,
            ]

        print(" ".join(sys_call))

        subprocess.check_call(sys_call)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", help="username for server", required=False)
    parser.add_argument("-p", "--password", help="password for server", required=False)
    parser.add_argument("--index", help="set url for package index", required=False)
    parser.add_argument(
        "--timeout", help="timeout for calls to server", default=60, type=int
    )

    parser.add_argument("--debug", help=argparse.SUPPRESS, default=None)

    subparsers = parser.add_subparsers(
        title="commands", description="available actions on the pypi server"
    )

    subparsers.required = True
    subparsers.dest = "command"
    parser_rem = subparsers.add_parser(
        "remove", help="remove a package version from the server"
    )
    parser_rem.add_argument("name", help="package name")
    parser_rem.add_argument("version", help="package version")
    parser_rem.set_defaults(func=remove)

    parser_list_parent = argparse.ArgumentParser(add_help=False)

    parser_list_parent.add_argument("name", help="package name", nargs="?")
    parser_list_parent.add_argument(
        "--version", help="package version or range, one or two arguments", nargs="+"
    )
    parser_list_parent.add_argument("--pyver", help="version of python3, e.g. 3.6")
    parser_list_parent.add_argument(
        "--platform", help="os name", choices=("linux", "macos")
    )

    parser_list = subparsers.add_parser(
        "list", help="list packages", parents=[parser_list_parent]
    )
    parser_list.set_defaults(func=package_list)

    parser_download = subparsers.add_parser(
        "download",
        help="download packages. Warning: with no filters all packages will be downloaded",
        parents=[parser_list_parent],
    )
    parser_download.add_argument(
        "-d", "--dest", help="directory to download to", default="."
    )
    parser_download.set_defaults(func=download)

    args = parser.parse_args()

    if None in (args.password, args.username, args.index):
        config_file = Path.home() / Path(".config/pypig/auth.json")
        if not config_file.exists():
            raise RuntimeError(
                "Username and password must be set by optional arguments or in $HOME/.config/pypig/auth.json"
            )
        with config_file.open() as f:
            varargs = vars(args)
            for key, val in json.load(f).items():
                if varargs[key] is None:
                    varargs[key] = val

    URL_PREFIX = "https://"

    if args.index.startswith(URL_PREFIX):
        args.url = f"{URL_PREFIX}{args.username}:{args.password}@{args.index[len(URL_PREFIX):]}"
    else:
        raise RuntimeError(f"Index url must begin with {URL_PREFIX}")
    args.func(args)


if __name__ == "__main__":
    main()
