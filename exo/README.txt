Where Are We? for DOSBox Staging
================================

Where Are We? is a companion tool for Might and Magic 1-3 and World of Xeen,
The Bard's Tale 1-3 and Wizardry I-V: automaps, party, monster, item and spell
information, quest lists. It was written by EDV Software (Eric Van Heest) and is
freeware: https://www.eskimo.com/~edv/lockscroll/WhereAreWe/

The original reads the memory of a DOSBox 0.74 process on Windows. This
unofficial port of its 1.2.0.0 development build reads the game through DOSBox
Staging's HTTP API instead (DOSBox Staging 0.83 or newer, with
webserver_enabled = on), so it works with DOSBox Staging, keeps working with
later versions, and runs on Linux and macOS too.

Builds:
- Windows: WhereAreWe.exe, needs the .NET Framework 4.8 (part of Windows 10 and
  11). This is the original's WinForms user interface.
- Linux x64, macOS (Apple silicon, Intel): the program "WhereAreWe", nothing to
  install. The same program on Majorsilence.Forms (Avalonia); windows look a
  little different. On macOS, a copy that came from a download has to be taken
  out of quarantine and signed ad hoc once before it runs:
      xattr -dr com.apple.quarantine <this folder>
      codesign --force --sign - <this folder>/WhereAreWe
  (the eXoDOS patch does this.)

Changes from the original:
- Game memory, the DOSBox window and the running program come from DOSBox
  Staging's API (127.0.0.1, port 8086 or 8080; Options > DOSBox to set another).
- The Bard's Tale III: also the THIEFP.EXE build (the one eXoDOS runs).
- Might and Magic III: the state is read right under eXoDOS's MM3.COM loader;
  the monster list is found with the MT-32 driver loaded too.
- World of Xeen: the CD version and the map scripts are found under DOSBox
  Staging's memory layout.
- The surface map images of the built-in maps are found next to the program
  (the original found them only in its current folder), also The Bard's
  Tale's Skara Brae map, which the built-in map names with a folder of the
  map author's machine.
- With a file named WhereAreWe.settings next to the program, the settings and
  the autosave file stay in this folder (an empty file is enough). Started
  that way with a game on the command line (-g, as eXoDOS does), there is no
  first-run setup wizard (Help > Run setup wizard still has it).
- Windows: while "Keep DOSBox window location" is set (Options, DOSBox tab;
  on by default), every run puts DOSBox at that location and the map,
  Game Info, Encounters and Party windows around it, in the room DOSBox
  leaves; other windows that would open over DOSBox open beside it. Window
  frames are measured right at any display scaling (the original was 7% off
  at 150%, so windows snapped beside each other).

Usage outside eXoDOS: start DOSBox Staging with
    [webserver]
    webserver_enabled = on
in its configuration, start the game, then Where Are We? (-g MM1, MM2, MM3,
MM45, BT1, BT2, BT3, WIZ1 ... WIZ5 picks the game). Put the surface map images
(WhereAreWe-Surface_Maps-v1.1.0.zip from the original's site) next to it.

The original's features for Eye of the Beholder and Ultima are left as they are
and were not tested.
