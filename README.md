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
