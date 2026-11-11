# 0004 JMdict compiled file, no word levels

Status: accepted. `tools/build_dictionary.py` filters JMdict and commits a 2.4 MB gzip so the game works right after
cloning. Every word is playable: there is no JLPT or frequency level, because the game is about finding Japanese
words, and difficulty comes only from the fuse and the lives. A commonness rank is kept per entry to order
suggestions, never to refuse a word. Memory: the loaded dictionary and indexes use about 130 MB of Python objects,
350 MB resident for the whole server.
