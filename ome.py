#! /usr/bin/env python


import argparse
import configparser
from datetime import datetime
import json
import os
import pathlib
import sys

from dateutil import parser
from mailmanclient import Client
import matplotlib.pyplot as plt
import pandas as pd


def remove_matching_mlists(mlists, days):
    deleted = {}
    utcnow = datetime.utcnow()
    for m in mlists:
        if m.settings["last_post_at"]:
            last_post_at = m.settings["last_post_at"]
            if last_post_at == "1970-01-01T00:00:00":
                created_at = m.settings["created_at"]
                not_used_for = (utcnow - parser.parse(created_at)).days
            else:
                not_used_for = (utcnow - parser.parse(last_post_at)).days
            if not_used_for >= days:
                m.delete()
                deleted.append(m.fqdn_listname)
            else:
                continue
    return deleted


def get_mlists_timedelta(mlists, days):
    extracted = {}
    utcnow = datetime.utcnow()
    for m in mlists:
        listinfo = {}
        if m.settings["last_post_at"]:
            last_post_at = m.settings["last_post_at"]
            if last_post_at == "1970-01-01T00:00:00":
                created_at = m.settings["created_at"]
                not_used_for = (utcnow - parser.parse(created_at)).days
            else:
                not_used_for = (utcnow - parser.parse(last_post_at)).days
            if not_used_for >= days:
                listinfo.update({
                    "last_post_at": last_post_at,

                    "not_used_for": not_used_for,
                })
            else:
                continue
            extracted[m.fqdn_listname] = listinfo
    return extracted


def get_config_data(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    if "omeconf" in config:
        root_url = config["omeconf"]["root_url"]
        restuser = config["omeconf"]["restuser"]
        restpass = config["omeconf"]["restpass"]
        return root_url, restuser, restpass
    else:
        print("Can not find a section omeconf", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(prog="ome.py")
    parser.add_argument(
        "days",
        help="Extract mailing lists not used for specified days or more",
        type=int)
    parser.add_argument(
        "-f",
        "--file",
        help="Specify an alternate config file")
    parser.add_argument(
        "-e",
        "--export",
        action="store_true",
        help="Export matching mailing lists as a json file")
    parser.add_argument(
        "-p",
        "--plot",
        action="store_true",
        help="Export a histogram")
    parser.add_argument(
        "-r",
        "--remove",
        action="store_true",
        help="Remove matching mailing lists")
    args = parser.parse_args()

    if args.file:
        p = pathlib.Path(args.file)
        if p.is_absolute():
            if os.path.isfile(p):
                root_url, restuser, restpass = get_config_data(p)
            else:
                print("{}: No such file".format(args.file), file=sys.stderr)
                sys.exit(1)
        else:
            if os.path.isfile(os.path.join(os.getcwd(), p)):
                root_url, restuser, restpass = get_config_data(p)
            else:
                print("{}: No such file".format(args.file), file=sys.stderr)
                sys.exit(1)
    else:
        root_url, restuser, restpass = get_config_data("./omeconf")

    client = Client(root_url, restuser, restpass)

    if args.remove:
        deleted = remove_matching_mlists(client.lists, args.days)
        print("Removed {} mailing lists".format(len(deleted)))
        sys.exit(0)

    extracted = get_mlists_timedelta(client.lists, args.days)

    if args.export:
        f = open("mlists.json", "w")
        json.dump(extracted, f)
        f.close()

    if args.plot:
        bins = int(len(extracted) / 2)
        plt.hist(pd.DataFrame(extracted).T["not_used_for"], bins=bins)
        plt.savefig("mlists.png")
        plt.close()

    for fqdn_listname in extracted:
        print("{}:\n \tNot used for {} days\n\tLast post at {}".format(
            fqdn_listname,
            extracted[fqdn_listname]["not_used_for"],
            extracted[fqdn_listname]["last_post_at"]))


if __name__ == "__main__":
    main()
