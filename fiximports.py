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

VERSION = "0.3Beta"

# python imports
import argparse
import logging
from datetime import date
import re
import sys,traceback

# gnucash imports
from gnucash import Session


def account_from_path(top_account, account_path, original_path=None):
    if original_path is None:
        original_path = account_path
    account, account_path = account_path[0], account_path[1:]
    account = top_account.lookup_by_name(account)
    if account is None or account.get_instance() is None:
        raise Exception(
            "A/C path " + ''.join(original_path) + " could not be found")
    if len(account_path) > 0:
        return account_from_path(account, account_path, original_path)
    else:
        return account


def readrules(filename):
    '''Read the rules file.
    Populate an list with results. The list contents are:
    ([pattern], [account name]), ([pattern], [account name]) ...
    Note, this is in reverse order from the file.
    '''
    rules = []
    with open(filename, 'r') as fd:
        for line in fd:
            line = line.strip()
            if line and not line.startswith('#'):
                if line.startswith('"'):
                    logging.debug('Using "-escpaped account in rule')
                    result = re.match(r"^\"([^\"]+)\"\s+(.+)", line)
                    if result:
                        ac = result.group(1)
                        pattern = result.group(2)
                        compiled = re.compile(pattern)  # Makesure RE is OK
                        rules.append((compiled, ac))
                        logging.debug('Found account %s and rule %s' % ( ac, pattern ) )
                    else:
                        logging.warn('Ignoring line: (incorrect format): "%s"', line)
                else:                       	       
                    result = re.match(r"^(\S+)\s+(.+)", line)
                    if result:
                        ac = result.group(1)
                        pattern = result.group(2)
                        compiled = re.compile(pattern)  # Makesure RE is OK
                        rules.append((compiled, ac))
                    else:
                        logging.warn('Ignoring line: (incorrect format): "%s"', line)
    return rules


def get_ac_from_str(str, rules, root_ac):
    for pattern, acpath in rules:
        if pattern.search(str):
            acplist = re.split(':', acpath)
            logging.debug('"%s" matches pattern "%s"', str, pattern.pattern)
            newac = account_from_path(root_ac, acplist)
            return newac
    return ""

# Parses command-line arguments.
# Returns an array with all user-supplied values.


def parse_cmdline():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--imbalance-ac', default="Imbalance-[A-Z]{3}",
                        help="Imbalance account name pattern. Default=Imbalance-[A-Z]{3}")
    parser.add_argument('--version', action='store_true',
                        help="Display version and exit.")
    parser.add_argument('-m', '--use_memo', action='store_true',
                        help="Use memo field instead of description field to match rules.")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Verbose (debug) logging.")
    parser.add_argument('-q', '--quiet', action='store_true',
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
        print(VERSION)
        exit(0)

    if args.verbose:
        loglevel = logging.DEBUG
    elif args.quiet:
        loglevel = logging.WARN
    else:
        loglevel = logging.INFO
    logging.basicConfig(level=loglevel)

    rules = readrules(args.rulesfile)
    account_path = re.split(':', args.ac2fix)

    gnucash_session = Session(args.gnucash_file, is_new=False)
    total = 0
    imbalance = 0
    fixed = 0
    try:
        root_account = gnucash_session.book.get_root_account()
        orig_account = account_from_path(root_account, account_path)

        imbalance_pattern = re.compile(args.imbalance_ac)

        for split in orig_account.GetSplitList():
            total += 1
            trans = split.parent
            splits = trans.GetSplitList()
            trans_date = trans.GetDate().date()
            trans_desc = trans.GetDescription()
            trans_memo = trans.GetNotes()
            for split in splits:
                ac = split.GetAccount()
                acname = ac.GetName()
                logging.debug('%s: %s => %s', trans_date, trans_desc, acname)
                if imbalance_pattern.match(acname):
                    imbalance += 1
                    search_str = trans_desc
                    if args.use_memo:
                        search_str = trans_memo
                    newac = get_ac_from_str(search_str, rules, root_account)
                    if newac != "":
                        logging.debug('\tChanging account to: %s', newac.GetName())
                        split.SetAccount(newac)
                        fixed += 1

        if not args.nochange:
            gnucash_session.save()

        logging.info('Total splits=%s, imbalance=%s, fixed=%s', total, imbalance, fixed)

    except Exception as ex:
        logging.error(ex) 

    gnucash_session.end()



if __name__ == "__main__":
    main()
