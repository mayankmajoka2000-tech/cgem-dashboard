# C-GEM Carbon Credit Intelligence - website source

Build files for the C-GEM carbon credit dashboard website (Apache Superset in Docker).
The Dockerfile rebuilds the site from the files part_00, part_01 and so on (one packed copy of dashboard version 78).
patch_v78.py holds the settings used only on the website (longer chart timeout, chart results cache).
