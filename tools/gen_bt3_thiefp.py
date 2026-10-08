"""Generate BT3ThiefPMemory.cs: BT3Memory's offsets plus the shifts measured between eXo's THIEF.EXE and
THIEFP.EXE RAM dumps (same GAME.SAV, Staging 0.84)."""
import re
import sys

src = open(sys.argv[1], encoding='utf-8').read()
base = {m.group(2): int(m.group(3)) for m in re.finditer(r'public (override|virtual) int (\w+) => (-?\d+);', src)}

groups = [
    ('far map segment', 2, 'Map MapSpecials MapSpecials2 MapTeleport MapFixedSquares ForcedEncounters MapCustomSquares '
                           'Wilderness MapSize MapSizeDungeons CurrentMonsters StateArray State3 MarchingOrder'),
    ('party and combat block (same data-segment offsets; the signature moved 18 bytes down)', 18,
     'PartyBonusAttacks TreasureRanges TreasureMinimums MapGoldMax CharCombatDamageBonus2 PartyCombatMagicResist '
     'PartyCombatOptions TrapType CharCombatDamageBonus EncounterMonstersKilled PartyNames PartyInfo CreationHP '
     'CreationRace PartyCombatSubOptions1 EnemyACBonus MonsterAC PartyCombatSelectedSpells EnemyDamageBonus '
     'MonsterDamage PartyCombatSubOptions2 MonsterIndices ImageCaption CombatActiveSpells State1 CombatSong '
     'PartyCombatACBonus CharCombatACBonus MonsterHP AdventuringSong'),
    (None, -6, 'ItemValues'),
    (None, -72, 'MonsterGroup'),
    (None, -118, 'MonsterExp'),
    (None, -308, 'SpellIcon1 SpellIcon2 SpellIcon3 SpellIcon4 SpellIcon5'),
    (None, -352, 'ItemList ItemCharges ItemDamage ItemACBonus ItemTypes ItemUsableBy ItemEquipEffect ItemEffects'),
    (None, -477, 'SwapWallsDoors'),
    (None, -711, 'MonsterNumAlive EnemyLoseTurn MonsterDistances TownMap MapStrings MapSquareStrings'),
    (None, -710, 'PartyPerishSeconds'),
    (None, -722, 'CastingChar'),
    (None, -766, 'NumItemsInShop ShopInventory CampInspectingChar'),
    (None, -1014, 'State4 TrapExamined ScreenText'),
    (None, -1016, 'SurfaceMapIndex MainMapIndex SubMapIndex LocationNorth LocationNorthTown LocationEast '
                  'LocationEastTown Facing FacingTown ScriptBits Counter1 GameTimeHours LightDistance SongDuration '
                  'LightDuration CompassDuration DetectionDuration ShieldDuration LevitationDuration MapFlags '
                  'MapTreasureIndex AdvPartyACBonus'),
    (None, -977, 'GameTimeSeconds'),
    (None, -978, 'SummonedCreature'),
    (None, -1840, 'AskWhichSpellCombat AskWhichSpellCombat2 State2 AskWhichSong AskWhichSpell ShopInspectingChar '
                  'ShoppingChar InspectingChar StackAddressIndicator'),
    ('stack frames: aligned by similarity only, the game code differs', -1844,
     'SelectedSpellSurfaceCombat SelectedSpellDungeonCombat SelectedSpellSurface SelectedSpellDungeon '
     'CombatActingChar3 CombatActingChar1 CombatActingChar2 CreationStats CreationStatsAlt CastingCharSurface NumChars '
     'CastingCharDungeon Stack'),
    (None, 258, 'TreasureState'),
]

out = ['namespace WhereAreWe;', '',
       "// THIEFP.EXE, the Bard's Tale III build eXoDOS runs: another compile of the game with the data segment laid",
       '// out differently around the same "refugee camp" signature. Offsets = THIEF.EXE\'s plus the shift measured',
       '// per block between RAM dumps of both builds in the same game state.',
       'public class BT3ThiefPMemory : BT3Memory', '{',
       '\t// The C runtime\'s "C_FILE_INFO" string (THIEF.EXE: 51300) tells the builds apart.',
       '\tpublic const int RuntimeFileInfoString = 50322;', '']
seen = set()
for comment, shift, names in groups:
    if comment:
        out.append(f'\t// {comment}')
    for n in names.split():
        assert n in base, n
        assert n not in seen, n
        seen.add(n)
        out.append(f'\tpublic override int {n} => {base[n] + shift};')
        out.append('')
out.append('\t// PSP+1Dh (file handle 5) and PSP+2Eh (SP saved by the last INT 21h): the program loads 6146 bytes closer')
out.append('\tpublic override int MapLoadingStatus => -200786;')
out.append('')
out.append('\tpublic override int StackOffsetIndex => -200769;')
seen.update({'MapLoadingStatus', 'StackOffsetIndex'})
out.append('}')
missing = sorted(set(base) - seen - {'MainBlockSVN', 'MainBlockOldSVN', 'MainBlockNonSVN', 'StackSize',
                                     'AskCastSpell', 'EncounterInfo'})
print('not shifted:', missing, file=sys.stderr)
assert base['MapLoadingStatus'] - base['StackOffsetIndex'] == -200786 - -200769
open(sys.argv[2], 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
