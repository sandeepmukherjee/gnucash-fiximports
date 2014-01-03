gnucash-fiximports
==================

Change target accounts of imported gnucash transactions

When GnuCash imports a OFX/QFX file, it adds all transactions to an
"Imbalance" account, typically "Imbalance-USD" (unless Bayesian matching
is enabled)
This script allows you to modify the target account according to rules
you create. For example, you can specify that a credit-card transaction
with a description starting with "PIZZA" be categorized as "Expenses:Dining".
To do this, you need to create a "rules" file first. See rules.txt for
more information on the format.
This script can search in the description or the memo fields.
For best results, disable Bayesian matching.

You must have python-bindings enabled.

This is currently in beta state, testing feedback will be appreciated!

Getting started
---------------

On Ubuntu you can simply install the Python bindings by:

    sudo apt-get install python-gnucash

Running the script on the example GnuCash file:

    ./fiximports.py -v 'Assets:Current Assets:Checking Account' examples/rules.txt examples/simple-checkbook.gnucash 

The above command line should apply the "pizza" and "salary" rule to the transactions in the checking account.

Run the script with "--help" to see all command line options:

    ./fiximports.py --help
