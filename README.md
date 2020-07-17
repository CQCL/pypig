# pypig

Command line utility for managing private pypiserver.
https://github.com/pypiserver/pypiserver

Install with `pip install -e .`

print help: `pypig -h`

for individual commands: `pypig <command> -h`

For frequent use store credentials in `${HOME}/.config/pypig/auth.json` as 

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