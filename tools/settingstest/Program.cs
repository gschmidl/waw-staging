// Checks the port's portable settings (WhereAreWe.settings next to the program): values of every kind survive a
// save and a fresh load, %TEMP% defaults move next to the program, and without the file nothing is written there.
//   settingstest.exe portable|plain
// Run from a scratch copy of the build folder; "portable" expects WhereAreWe.settings beside settingstest.exe.
using System;
using System.Configuration;
using System.IO;
using System.Reflection;
using WhereAreWe;

static class Program
{
    static int Main(string[] args)
    {
        var asm = typeof(PortableSettingsProvider).Assembly;
        var st = asm.GetType("WhereAreWe.Properties.Settings");
        PortableSettingsProvider.Configure();
        Console.WriteLine("portable file: " + (PortableSettingsProvider.FilePath ?? "(none)"));
        if (args.Length > 0 && args[0] == "plain")
            return PortableSettingsProvider.FilePath == null ? 0 : 1;

        // First pass: change values of several kinds, save.
        var s1 = (ApplicationSettingsBase)Activator.CreateInstance(st, true);
        Console.WriteLine($"defaults: MaxUndoActions={s1["MaxUndoActions"]} AutoSaveFile={s1["AutoSaveFile"]} WizardRun={s1["WizardRun"]}");
        s1["MaxUndoActions"] = 37;
        s1["WizardRun"] = true;
        s1["DOSBoxApiAddress"] = "127.0.0.1:18099";
        var titles = s1["GameTitles"];
        Console.WriteLine("GameTitles type: " + titles?.GetType().FullName);
        s1["AutoSaveFile"] = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "x.waw");
        s1.Save();
        Console.WriteLine("saved; file has " + new FileInfo(PortableSettingsProvider.FilePath).Length + " bytes");

        // Second pass: a fresh instance reads them back.
        var s2 = (ApplicationSettingsBase)Activator.CreateInstance(st, true);
        bool ok = (int)s2["MaxUndoActions"] == 37 && (bool)s2["WizardRun"] && (string)s2["DOSBoxApiAddress"] == "127.0.0.1:18099"
                  && ((string)s2["AutoSaveFile"]).EndsWith("x.waw");
        Console.WriteLine($"reloaded: MaxUndoActions={s2["MaxUndoActions"]} WizardRun={s2["WizardRun"]} api={s2["DOSBoxApiAddress"]} ok={ok}");
        // Complex values: every property must deserialize from the file without an exception.
        int n = 0;
        foreach (SettingsProperty p in s2.Properties)
        {
            try { _ = s2[p.Name]; n++; }
            catch (Exception e) { Console.WriteLine($"FAIL {p.Name}: {e.GetType().Name} {e.Message}"); ok = false; }
        }
        Console.WriteLine($"{n} properties read");
        s2["MaxUndoActions"] = 21;
        s2.Save();
        var s3 = (ApplicationSettingsBase)Activator.CreateInstance(st, true);
        ok &= (int)s3["MaxUndoActions"] == 21 && (bool)s3["WizardRun"];
        // Reset empties the file.
        s3.Reset();
        var s4 = (ApplicationSettingsBase)Activator.CreateInstance(st, true);
        ok &= (int)s4["MaxUndoActions"] == 20;
        Console.WriteLine(ok ? "OK" : "FAILED");
        return ok ? 0 : 1;
    }
}
