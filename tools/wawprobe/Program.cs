// Command-line probe for the Where Are We? port's DOSBox Staging API layer.
//   wawprobe info  [host:port]            API version, RAM size, running program, synthesized title
//   wawprobe scan  <game> [host:port]     Init() the game's memory hacker and print what it reads
//   wawprobe dump  <file> [host:port]     save the emulated RAM to a file
//   wawprobe watch <game> [host:port]     scan, then print location/state changes until Ctrl+C
//   wawprobe teleport <game> host:port x,y  move the party with the hacker's SetLocation
using System;
using System.IO;
using System.Linq;
using System.Threading;
using WhereAreWe;
#if MAJORSILENCE_FORMS
using Keys = Majorsilence.Forms.Keys;
#else
using Keys = System.Windows.Forms.Keys;
#endif

static class Program
{
    static int Main(string[] args)
    {
        if (args.Length == 0) { Console.Error.WriteLine("usage: wawprobe info|scan|dump|watch ..."); return 2; }
        string addr = args.Length > (args[0] == "info" ? 1 : 2) ? args[args[0] == "info" ? 1 : 2] : null;
        if (args[0] == "parent") addr = args.Length > 2 ? args[2] : null;
        DosboxApi.Address = addr;
        Global.MemoryGuesses = new MemoryGuesses();
        if (!DosboxApi.IsAlive) { Console.WriteLine("no DOSBox Staging API answered"); return 1; }
        Console.WriteLine($"API: {DosboxApi.Version} port {DosboxApi.Port}, RAM {DosboxApi.RamSize} bytes");
        switch (args[0])
        {
            case "info":
                Console.WriteLine($"program: '{DosboxApi.RunningProgram()}'");
                Console.WriteLine($"title:   '{DosboxApi.WindowTitle}'");
                Console.WriteLine($"known game: {MemoryHacker.FindKnownGame()}");
                return 0;
            case "dump":
            {
                var ram = new byte[DosboxApi.RamSize];
                if (!DosboxApi.Read(0, ram, 0, ram.Length)) { Console.WriteLine("read failed: " + DosboxApi.LastError); return 1; }
                File.WriteAllBytes(args[1], ram);
                Console.WriteLine($"wrote {ram.Length} bytes to {args[1]}");
                return 0;
            }
            case "teleport":
            {
                var hacker = Games.CreateHacker(Games.GameEnumFromShort(args[1]));
                hacker.Stop();
                if (!hacker.Init()) { Console.WriteLine("Init failed"); return 1; }
                Console.WriteLine("before: " + Describe(hacker));
                var xy = args[3].Split(',');
                bool ok = hacker.SetLocation(new System.Drawing.Point(int.Parse(xy[0]), int.Parse(xy[1])));
                Thread.Sleep(500);
                Console.WriteLine($"SetLocation: {ok}");
                Console.WriteLine("after:  " + Describe(hacker));
                return 0;
            }
            case "parent":
                Console.WriteLine("parent of PSP at " + args[1] + ": '" + DosboxApi.ParentProgram(Convert.ToInt64(args[1], 16)) + "'");
                return 0;
            case "keys":
            {
                var hacker = Games.CreateHacker(Games.GameEnumFromShort(args[1]));
                hacker.Stop();
                if (!hacker.Init()) { Console.WriteLine("Init failed"); return 1; }
                Console.WriteLine("before: " + Describe(hacker));
                hacker.DOSBoxWindow = DosboxApi.PseudoWindow;
                var keys = args[3].Split(',').Select(k => (Keys)Enum.Parse(typeof(Keys), k)).ToArray();
                bool ok = hacker.SendKeysToDOSBox(keys);
                Thread.Sleep(1500);
                Console.WriteLine($"SendKeysToDOSBox: {ok}");
                Console.WriteLine("after:  " + Describe(hacker));
                return 0;
            }
            case "scan":
            case "watch":
            {
                GameNames game = Games.GameEnumFromShort(args[1]);
                if (game == GameNames.None) { Console.WriteLine("unknown game " + args[1]); return 2; }
                var hacker = Games.CreateHacker(game);
                hacker.Stop();
                var t0 = DateTime.Now;
                bool ok = hacker.Init();
                Console.WriteLine($"Init({game}): {ok} in {(DateTime.Now - t0).TotalMilliseconds:F0} ms; found offset {hacker.FoundBlockOffset} (linear {(long)hacker.FoundBlockOffset - DosboxApi.BlockHeader:X}); needs reinitialize {hacker.NeedsReinitialize}");
                Console.WriteLine(hacker.GetDebugMemoryInfo());
                if (!ok) return 1;
                string last = null;
                do
                {
                    string now = Describe(hacker);
                    if (now != last) { Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] " + now); last = now; }
                    if (args[0] == "watch") Thread.Sleep(250);
                } while (args[0] == "watch");
                return 0;
            }
        }
        return 2;
    }

    static string Describe(MemoryHacker hacker)
    {
        try
        {
            var gs = hacker.GetGameState();
            var loc = gs?.Location;
            var chars = hacker.GetCharacters();
            return $"ready={hacker.GameReady} main={gs?.Main} combat={gs?.InCombat} map={loc?.MapIndex} xy={loc?.PrimaryCoordinates} facing={loc?.Facing} chars=[{(chars == null ? "" : string.Join(", ", chars.Select(c => c.Name)))}] states={gs?.StateString}";
        }
        catch (Exception e) { return "EXCEPTION " + e.GetType().Name + ": " + e.Message; }
    }
}
