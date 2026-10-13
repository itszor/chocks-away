Chocks Away (Andrew Hutchings / The Fourth Dimension, 1990) - static recompilation
===================================================================================

A recipe: this repository holds no game data. It rebuilds the game as a
native executable from your own copy of the discs, recognised by content
(recipe.json), so it can be shared without distributing the game.

    ./build.sh "Chocks Away (1990)(Fourth Dimension).zip"    (or the .adf files)
    cd recomp && ./chocksaway

build.sh runs recipe.json's steps with SuperSpider's tools/weave.py
(~/stuff/superspider, or $SUPERSPIDER): it finds the program and maps discs
among the inputs, extracts them, assembles the machine code, analyses and
translates it, translates the BASIC, and links it all with libroger
(~/stuff/libroger, or make ROGER=...). It takes about five minutes, most of
it SuperSpider's analysis. Needs python3, OCaml/dune, gcc and SDL3.

Inputs: the TOSEC set's `Chocks Away (1990)(Fourth Dimension).zip`, or the
two disc images from it: `(Disk 1 of 3).adf` (the program) and `(Disk 2 of
3)(Maps Disk).adf`. The `[a]` dumps match the recipe only in part (94%:
their disc 1 has a different ChocksAway BASIC, and extracts with errors),
so they aren't built from. Disc 3 (the Extra Missions add-on) isn't used
yet.

What it makes:

    extracted/disc1, disc2   $SS/tools/adf_extract.py's output, via weave.py
    game/                    !Chocks and !Maps from them: libroger's appdir
    unpacked/core            the machine code and tables as the BASIC lays them
                             out, &11170-&903E4 (tools/images.py assemble)
    analysis/*.json          SuperSpider's analyses (core, Mix, the modules)
    recomp/gen/              their C translations; recomp/basic.c the BASIC's
    recomp/chocksaway        the game

Committed: recipe.json, build.sh, tools/images.py, recomp/ (Makefile,
game.c), analysis/core.roots, this file.

How the game is put together
----------------------------

!Run sets a 600K WimpSlot and runs !Changes (a utility setting the dynamic
areas: 160K of screen for two mode 13 banks) and !Setup, a BASIC loader:
the title picture (*ScreenLoad), the Joystick module (Keith Martin, 1990)
and five Fourth Dimension sound modules, the sprites and the character
set. It CHAINs !Chocks.ChocksAway, the front end in BASIC (menus, mission
briefings, high scores, the flight recorder), which loads the machine code
and its tables at fixed addresses inside its first `DIM C% 549000` and
CALLs it: Code (&1ADB0) flies one player, Code2 (&11170) two, split screen;
both also draw the menu's spinning biplane and the target views.

- recomp/basic.c: the BASIC, translated by $SS/tools/bas2c.py, on
  SuperSpider's BASIC runtime ($SS/runtime/basic_runtime.c), its heap
  (bas_lomem, in game.c) at this program's TOP, &10300, so the DIMs land
  where the code expects them.
- recomp/game.c: !Setup by hand; SETUP (the utility that loads Code and
  Code2 and waits for a key on the title, F being the cheat: --cheat);
  the one assembler statement (the flight recorder's directory name); the
  quit (the BASIC resets the machine: here the program ends).
- Mix (the briefing room's map) is *LOADed into a DIMmed block and CALLed:
  translated as an overlay at that block's address (&96D58).

The flight code keeps return addresses in words of its own (`str lr,[pc,#k]`
... `ldr lr,[pc,#j] ; mov pc,lr`); SuperSpider's memory mechanism now
follows that. Everything translates: headless runs through the menus, a
briefing and a flight interpret nothing.

Speed and sound
---------------

The flight waits for the next vsync between frames and moves everything
a step a frame, so its speed was the machine's: a frame is about 150,000
instructions, 17-25 frames a second on an 8MHz ARM2. Translated, it
would run at 50. game.c sets libroger's CPU speed to 4.5 MIPS, an ARM2's
(about 21 frames a second, slower in busy scenes as on the original):
--mips=N to change it, --mips=0 for flat out.

Sound needed two things from libroger: the system clock (OS_Word 1/2,
which the engine noise is timed by) and voice numbers as RISC OS 3.1
gives them (its ROM has voices 1-9, so the game's five modules are 10-14,
and it attaches its channels to 10, 13 and 14 by number). F1/F2 turn the
volume down/up, F3 the speaker off/on (the game's own keys).

Controls
--------

Menus: the mouse (or the keys below). Flying, player 1: X/C roll left/right,
Z climb, A dive, V fire, left Ctrl throttle up, left Shift throttle down
(the original's Controls file). Player 2: keypad 2/3, +/-, Enter, 4/1.

A headless scenario (MISSIONS, mission 1, its briefing, then throttle up
and a climb; screenshot-N.bmp):

    ./chocksaway --limit=1.6e9 --full-os --script=1000:click:200:300,1300:release,\
    10000:click:880:800,10300:release,32000:click:640:100,32300:release,\
    36000:key:5:25000,45000:shot,62000:key:98:3000,66000:shot,75000:shot

Not done
--------

- Disc 3, the Extra Missions add-on (its program extracts as an empty file:
  an old-map disc).
- The flight recorder (REPLAY FLIGHT, RECORDER ON) isn't tried: it saves
  to and lists adfs::0.$.!BLACKBOX, a separate "black box" disc, and calls
  ADFS_FreeSpace, which libroger doesn't have.
- Joysticks (the Joystick module's podule).
