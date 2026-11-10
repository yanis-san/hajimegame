# 0004 JMdict compiled file, frequency-based levels

Status: accepted. `tools/build_dictionary.py` filters JMdict and commits a 2.4 MB gzip so the game works right after
cloning. JLPT no longer publishes lists, so N5 to N1 are thresholds on JMdict frequency ranks (see
`docs/DICTIONARY.md`); the thresholds are data and can be replaced by a community list. Memory: the loaded dictionary
and indexes use about 130 MB of Python objects, 350 MB resident for the whole server.
