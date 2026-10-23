/* Chocks Away (Andrew Hutchings / The Fourth Dimension, 1990): what
 * libroger needs to know about the game.
 *
 * !Run: WimpSlot 600K, then !Changes (sets the dynamic areas: 160K of
 * screen, two mode 13 banks) and !Setup, a BASIC loader (setup() below,
 * by hand): the title picture, the sound and joystick modules, the
 * sprites and character set. It CHAINs !Chocks.ChocksAway, the game's
 * front end (basic.c, translated by SuperSpider's tools/bas2c.py), which
 * *LOADs the machine code and tables at fixed addresses (most by its own
 * OSCLIs, Code and Code2 through the SETUP utility) and CALLs it: the
 * flight itself (Code: one player, Code2: two, split screen).
 * Discs 1 and 2 are merged into ../game (!Chocks, !Maps).
 *
 * Or the Compendium (Mark 2, 1991): the same Code, Code2 and tables, behind
 * the ZFiler protection - the module serves them, and the BASIC, from
 * !Chocks.<160> (weave.py reveals them there) - and a BASIC that *LOADs
 * Code and Code2 itself (no SETUP), turns ZFiler off when it has them
 * (ZFiler_Set 1), and quits to the desktop.
 *
 * Or the Compendium's RISC OS 4 + StrongARM release (2000), one disc: the
 * same code, tables and maps again (the maps in !Chocks.Maps), packed by
 * the Fourth Dimension's DeComp module, whose *CLoad the BASIC loads them
 * with (the module runs, translated). Its !Run also loads PowerEater
 * (M. Allcorn, 1999), which slows a fast machine down to the game's speed
 * by eating cycles every centisecond: here libroger's CPU speed (.mips)
 * does that. Its BASIC *CLOADs Code and Code2 itself too, and quits to
 * the desktop. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "basic_runtime.h"

/* the core image's translation (make regen): Code2, Code and the tables
 * from &11170, as the BASIC lays them out (../unpacked/core). It's
 * loaded up front, and DIM C% leaves it there, as BASIC does (the runtime's
 * bas_dim_clear off); the BASIC's *LOADs then write the same bytes over it,
 * which leaves the translation in place - DeComp's *CLoads too, though
 * they're stores from translated code: each word is still what it was. */
extern const struct roger_image recomp_image;
extern int32_t J_I;                              /* the BASIC's J%: the joystick, as !Setup found it */

#include "gen/modules.inc"      /* Joystick and the sound modules; MIX_ADDRESS */

/* the BASIC runtime ($SS/runtime/basic_runtime.c): PAGE, the default, after
 * !Setup CHAINs it; the heap above the program (PAGE + its 29696 bytes:
 * &10300; the later releases' are shorter) - the game's code and tables
 * are at fixed addresses inside the first block, DIM C% 549000 (526000 in
 * 2000) (../tools/images.py) */
int32_t bas_page = 0x8F00;
uint32_t bas_lomem = BAS_LOMEM;

/* Mix, which the BASIC *LOADs into DIM MIX 500 and CALLs (the briefing
 * room's picture), translated for that block's address */
extern const struct roger_image recomp_mix_image;
static const struct roger_program programs[] = {{"Mix", &recomp_mix_image, 1}, {NULL, NULL, 0}};

/* the game's filenames: adfs::0.$.!CHOCKS.x, ADFS::0.$.!MAPS.x (any case),
 * and SETUP's :0.!CHOCKS.x; the 2000 release's <Chocks$Dir>.x (its !Boot's) */
static const char *const prefixes[] = {"adfs::0.$.", ":0.", NULL};
static const char *const variables[] = {"Chocks$Dir", "!Chocks", NULL};

static int cheat;                                /* --cheat: press F at the title */

#define CHEAT_WORD 0x1D1B4                       /* in Code: what SETUP's F clears */

static int game_arg(const char *a)
{
    if (strcmp(a, "--cheat")) return 0;
    cheat = 1;
    return 1;
}

/* !Chocks.SETUP, a utility the BASIC runs: it loads the code, then waits for
 * a key on the title picture (its prompt is printed black on black). F is
 * the cheat: it beeps and clears the word at &1D1B4. */
static void run_setup(void)
{
    static const char msg[] = "  THE FOX! WAZ EAR....Press F to cheat  ";
    vdu(17, 191, 17, 0, -1);
    roger_cli("LOAD :0.!CHOCKS.Code 1ADB0");
    roger_cli("LOAD :0.!CHOCKS.Code2 11170");
    for (const char *p = msg; *p; p++) vdu((uint8_t)*p, -1);
    R[0] = 21; R[1] = 0; roger_swi(0x06);        /* flush the keyboard buffer */
    roger_swi(0x04);                             /* OS_ReadC */
    if (cheat || R[0] == 'F') {
        vdu(7, -1);
        WR32(CHEAT_WORD, 0);
    }
}

/* ZFiler (the Mark 2's protection, SWIs from &94700): the BASIC's SYS
 * "ZFiler_Set",1 turns it off. Here its files are plain ones, so it's a
 * name and a SWI that do nothing. */
static int game_swi(uint32_t n, int x)
{
    (void)x;
    n &= ~0x20000u;
    if (n == 0x39 && (!strcmp((const char *)MEM + R[1], "ZFiler_Read") || !strcmp((const char *)MEM + R[1], "ZFiler_Set"))) {
        R[0] = 0x94700 + (MEM[R[1] + 7] == 'S');
        return 1;
    }
    return n == 0x94700 || n == 0x94701;
}

/* DeComp's *CLOAD file addr (the 2000 release's): the module unpacks the
 * file into place (translated code storing it), so it's told to libroger
 * as a load - Mix is a program translated for where it lands. No SETUP
 * here either: --cheat clears the word as Code arrives. */
static int cload(const char *c)
{
    char name[256];
    unsigned addr;
    if (strncasecmp(c, "CLOAD ", 6) || sscanf(c + 6, "%255s %x", name, &addr) != 2) return 0;
    roger_cli(c);
    roger_program_loaded(name, addr);
    if (cheat && addr == 0x1ADB0) WR32(CHEAT_WORD, 0);
    return 1;
}

static int game_cli(const char *c)
{
    while (*c == ' ' || *c == '*') c++;
    if (!strcasecmp(c, "ADFS::0.$.!CHOCKS.SETUP")) { run_setup(); return 1; }
    /* the Mark 2 has no SETUP, so no cheat key: --cheat clears the word as
     * Code arrives (LOAD ADFS::0.$.!Chocks.<160>.Code 1ADB0) */
    if (cheat && !strncasecmp(c, "LOAD ", 5) && strstr(c, "\240.Code ")) {
        roger_cli(c);
        WR32(CHEAT_WORD, 0);
        return 1;
    }
    if (cload(c)) return 1;
    /* PowerEater's: on, off (the 2000 release's BASIC) - .mips paces the game */
    if (!strcasecmp(c, "PEON") || !strcasecmp(c, "PEOFF")) return 1;
    /* PROCQUIT: *FX 25, MODE 0, *SNEW, *RMCLEAR, then !0 = the ROM's first
     * word and CALL RESET (a branch through zero): the machine resets (the
     * later releases quit to the desktop) */
    if (!strcasecmp(c, "SNEW")) roger_finish("quit");
    return 0;
}

/* the assembler, used once: PROCCAT's [OPT 2: EQUS "adfs::0.$.!BLACKBOX"+DIR$:
 * EQUB 0:] at P% = SPARE, the black box (recordings) directory's name.
 * DIR$ is "" for one player, "2" for two (line 110, from Q%). */
void bas_asm(const char *text)
{
    extern int32_t P_I, Q_I;
    if (strstr(text, "EQUS adfs::0.$.!BLACKBOX + DIR$ : EQUB 0")) {
        snprintf((char *)MEM + P_I, 32, "adfs::0.$.!BLACKBOX%s", Q_I == 1 ? "" : "2");
        P_I += (int32_t)strlen((char *)MEM + P_I) + 1;
    } else fprintf(stderr, "bas_asm: not handled: %s\n", text);
}

/* !Setup (BASIC, by hand) */
static void setup(void)
{
    mode(13);
    roger_swi(0x36);                             /* OS_RemoveCursors */
    oscli_c("SCREENLOAD adfs::0.$.!Chocks.!Piccy");
    vdu(19, 1, 24, 255, 255, 255, -1);
    roger_swi(swi_number("Wimp_CloseDown"));
    static const char *const mods[] = {"JOYSTICK", "GUNMD2", "WHEELMD", "EXPLODEMD2", "EXPLODEMD3", "ENGINE"};
    char cmd[80];
    for (int k = 0; k < 6; k++) {
        snprintf(cmd, sizeof cmd, "RMLOAD adfs::0.$.!CHOCKS.SOUNDS.%s", mods[k]);
        oscli_c(cmd);
        if (k == 0) {                            /* SYS &CFFC0 TO J%: Joystick's first SWI */
            roger_swi(0xCFFC0);
            J_I = (int32_t)R[0];
        }
    }
    for (const struct roger_module *m = modules; m->path; m++)   /* the 2000 release's */
        if (strstr(m->path, "/DeComp,")) oscli_c("RMLOAD adfs::0.$.!CHOCKS.SOUNDS.DECOMP");
    oscli_c("SLOAD adfs::0.$.!CHOCKS.SPRITES.SPRITES");
    oscli_c("SMERGE adfs::0.$.!CHOCKS.SPRITES.2PLAYER");
    oscli_c("adfs::0.$.!CHOCKS.SPRITES.CHOCKCHAR");
}

static void init(void)
{
    bas_cli = game_cli;
    setup();
    bas_main();                                  /* CHAIN "adfs::0.$.!Chocks.CHOCKSAWAY" */
    roger_finish("program ended");
}

static struct roger_config config = {
    .title = "Chocks Away (recompiled)",
    /* controllers: the stick or D-pad flies (X/C roll, A dive pushing, Z
     * climb pulling), A fire (V), the right trigger or shoulder throttle up
     * (left Ctrl), the left ones down (left Shift); a second controller is
     * player 2 (keypad 2/3 roll, - dive, + climb, Enter fire, 4/1 throttle) */
    .pad_map = "left=X,right=C,up=A,down=Z,a=V,rt=Left Ctrl,rb=Left Ctrl,lt=Left Shift,lb=Left Shift",
    .pad2_map = "left=Keypad 2,right=Keypad 3,up=Keypad -,down=Keypad +,a=Keypad Enter,rt=Keypad 4,rb=Keypad 4,lt=Keypad 1,lb=Keypad 1",
    /* the controllers as the joystick, if one is connected: Joy_Read0 and
     * Joy_Read1, the two players' (instead of the Joystick module's) */
    .joystick = ROGER_JOY_KM,
    .image_path = "../unpacked/core",
    .image = &recomp_image,
    .modules = modules,
    .programs = programs,
    .appdir = "../game",
    .dir_prefixes = prefixes,
    .variables = variables,
    .initial_mode = 13,
    .wimpslot = 600 * 1024,
    .screen_size = 0x28000,                      /* !Changes */
    .interpret_gaps = 1,
    /* The flight doesn't pace itself beyond waiting for the next vsync,
     * and moves the planes a step a frame: translated, it would run at 50
     * frames a second. An 8MHz ARM2's speed (a frame is ~150,000
     * instructions: 17-25 frames a second, slower in busy scenes, as on
     * an A3000); --mips=N to change it, 0 for flat out */
    .mips = 4.5,
    .init = init,
    .arg = game_arg,
    .swi = game_swi,
    .usage = "  --cheat           the cheat SETUP offers (F at the title picture)\n",
};

int main(int argc, char **argv) { roger_main(argc, argv, &config); }
