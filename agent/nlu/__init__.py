"""Schema-guided language understanding for one dialogue turn.

The tenant's own published data is the schema: its brands, product families and
attribute values are the slot vocabularies, so a new vertical needs no code here
(the schema-guided approach of Rastogi et al., DSTC8/SGD).

Modules:

* ``lexical``    - scored alignment between spoken words and published values
* ``schema``     - slot vocabularies derived from tenant records
* ``frame``      - the semantic frame: constraints separated from operators
* ``resolution`` - candidate scoring and the act-or-ask decision
"""
