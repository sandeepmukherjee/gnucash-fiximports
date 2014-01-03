#!/usr/bin/env python

# fiximports.py -- Categorize imported transactions according to user-defined
#                  rules.
#
# Copyright (C) 2013 Sandeep Mukherjee <mukherjee.sandeep@gmail.com>
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, contact:
# Free Software Foundation           Voice:  +1-617-542-5942
# 51 Franklin Street, Fifth Floor    Fax:    +1-617-542-2652
# Boston, MA  02110-1301,  USA       gnu@gnu.org
#

# @file
#   @brief Categorize imported transactions according to user-defined rules.
#   @author Sandeep Mukherjee <mukherjee.sandeep@gmail.com>
#
# When GnuCash imports a OFX/QFX file, it adds all transactions to an
# "Imbalance" account, typically "Imbalance-USD" (unless Bayesian matching
# is enabled)
# This script allows you to modify the target account according to rules
# you create. For example, you can specify that a credit-card transaction
# with a description starting with "PIZZA" be categorized as "Expenses:Dining".
# To do this, you need to create a "rules" file first. See rules.txt for
# more information on the format.
# This script can search in the description or the memo fields.

VERSION = "0.2Beta"

# python imports
import argparse
from datetime import date
import re

# gnucash imports
from gnucash import Session


def account_from_path(top_account, account_path, original_path=None):
    if original_path == None:
        original_path = account_path
    account, account_path = account_path[0], account_path[1:]
    account = top_account.lookup_by_name(account)
    if account.get_instance() == None:
        raise Exception(
            "path " + ''.join(original_path) + " could not be found")
    if len(account_path) > 0:
        return account_from_path(account, account_path, original_path)
    else:
        return account

# Read the rules file.
# Populate an array with results. The array contents are:
# [pattern] [account name] [pattern] [account name] ...
# Note, this is in reverse order from the file.


def readrules(filename):
    rules = []
    fp = open(filename, 'r')
    for line in fp:
        # print line
        if line[0] != "#" or re.match("^\s*#", line):
            result = re.match(r"^(\S+)\s+(.+)", line)
            if result:
                ac = result.group(1)
                pattern = result.group(2)
                re.compile(pattern)  # Makesure RE is OK
                rules.append(pattern)
                rules.append(ac)
            else:
                print "Ignoring line: (incorrect format):", line
    return rules


def get_ac_from_str(str, rules, root_ac):
    rlen = len(rules)
    for i in range(0, rlen, 2):
        if re.search(rules[i], str):
            acpath = rules[i + 1]
            acplist = re.split(':', acpath)
            # print str, "matches", rules[i]
            newac = account_from_path(root_ac, acplist)
            return newac
    # print str, "does not match anything"
    return ""

# Parses command-line arguments.
# Returns an array with all user-supplied values.


def parse_cmdline():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--imbalance-ac', default="Imbalance-USD",
                        help="Imbalance account name. Default=Imbalance-USD")
    parser.add_argument('-v', '--version', action='store_true',
                        help="Display version and exit.")
    parser.add_argument('-m', '--use_memo', action='store_true',
                        help="Use memo field instead of description field to match rules.")
    parser.add_argument('-s', '--silent', action='store_true',
                        help="Suppress normal output (except errors).")
    parser.add_argument('-n', '--nochange', action='store_true',
                        help="Do not modify gnucash file. No effect if using SQL.")
    parser.add_argument(
        "ac2fix", help="Full path of account to fix, e.g. Liabilities:CreditCard")
    parser.add_argument("rulesfile", help="Rules file. See doc for format.")
    parser.add_argument("gnucash_file", help="GnuCash file to modify.")
    args = parser.parse_args()

    return args

# Main entry point.
# 1. Parse command line.
# 2. Read rules.
# 3. Create session.
# 4. Get a list of all splits in the account to be fixed. For every split:
#     4.1: Lookup up description or memo fied.
#     4.2: Use the rules to check if a matching account can be located.
#     4.3: If there is a matching account, set the account in the split.
# 5. Print stats and save the session (if needed).


def main():
    args = parse_cmdline()
    if args.version:
        print VERSION
        exit(0)
    rules = readrules(args.rulesfile)
    account_path = re.split(':', args.ac2fix)

    gnucash_session = Session(args.gnucash_file, is_new=False)
    root_account = gnucash_session.book.get_root_account()
    orig_account = account_from_path(root_account, account_path)

    total = 0
    imbalance = 0
    fixed = 0
    for split in orig_account.GetSplitList():
        total += 1
        trans = split.parent
        splits = trans.GetSplitList()
        trans_date = date.fromtimestamp(trans.GetDate())
        trans_desc = trans.GetDescription()
        trans_memo = trans.GetNotes()
        ac = splits[0].GetAccount()
        acname = ac.GetName()
        if not args.silent:
            print trans_date, ":", trans_desc, "=>", acname
        # check if acname is "Imbalance-USD"
        if acname == args.imbalance_ac:
            imbalance += 1
            search_str = trans_desc
            if args.use_memo:
                search_str = trans_memo
            newac = get_ac_from_str(search_str, rules, root_account)
            if newac != "":
                if not args.silent:
                    print "\t Changing account to: ", newac.GetName()
                splits[0].SetAccount(newac)
                fixed += 1

    if not args.nochange:
        gnucash_session.save()
    gnucash_session.end()

    if not args.silent:
        print "Total splits=", total, " imbalance=", imbalance, " fixed=", fixed


if __name__ == "__main__":
    main()
