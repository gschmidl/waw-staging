// Headless twin of tools/wawshot for the Majorsilence.Forms build: runs MainForm in-process on the
// Headless backend and saves each open form as a PNG, optionally after clicking menu items.
//   WAWSHOT_OUT, WAWSHOT_API, WAWSHOT_DELAY (ms, default 4000), WAWSHOT_STEPS (;-separated menu fields)
// Command-line arguments go to Where Are We? itself (e.g. -g mm1).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using Majorsilence.Forms;
using Majorsilence.Forms.Headless;
using WhereAreWe;

static class Program
{
    static string s_out;
    static int s_shot;
    static int s_dialogs;
    static readonly List<string> s_log = new List<string>();
    static readonly List<WindowBase> s_windows = new List<WindowBase>();

    static void Log(string s) { s_log.Add($"{DateTime.Now:HH:mm:ss.fff} {s}"); File.WriteAllLines(Path.Combine(s_out, "wawshot.log"), s_log); }

    [STAThread]
    static int Main()
    {
        s_out = Environment.GetEnvironmentVariable("WAWSHOT_OUT") ?? ".";
        Directory.CreateDirectory(s_out);
        int delay = int.TryParse(Environment.GetEnvironmentVariable("WAWSHOT_DELAY"), out int d) ? d : 4000;
        var steps = new Queue<string>((Environment.GetEnvironmentVariable("WAWSHOT_STEPS") ?? "").Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries));
        Environment.SetEnvironmentVariable("WAW_DOSBOX_API", Environment.GetEnvironmentVariable("WAWSHOT_API"));
        HeadlessRenderer.Use();

        var asm = typeof(MainForm).Assembly;
        var st = asm.GetType("WhereAreWe.Properties.Settings");
        var def = st.GetProperty("Default").GetValue(null);
        st.GetProperty("WizardRun").SetValue(def, true);

        var main = new MainForm();
        // Dialogs would block this loop: log and capture them, then close them.
        var dismisser = new Majorsilence.Forms.Timer { Interval = 300 };
        dismisser.Tick += (s, e) =>
        {
            foreach (Form f in Application.OpenForms.Cast<Form>().ToList())
            {
                if (f == main || !f.Visible || !(f is MessageBoxForm || f.Modal)) continue;
                string text = f is MessageBoxForm mb ? mb.Message : f.Text;
                Log($"dialog {f.GetType().Name} '{f.Text}': {text}");
                try { File.WriteAllBytes(Path.Combine(s_out, $"dialog_{++s_dialogs:00}_{f.GetType().Name}.png"), HeadlessRenderer.CapturePng(f, f.Width, f.Height)); } catch (Exception) { }
                f.DialogResult = DialogResult.Cancel;
                f.Close();
            }
        };
        dismisser.Start();
        main.Show();
        var t0 = DateTime.Now;
        int nextAt = delay;
        while (true)
        {
            Application.DoEvents();
            Thread.Sleep(15);
            if ((DateTime.Now - t0).TotalMilliseconds < nextAt) continue;
            CaptureAll(main);
            if (steps.Count == 0) break;
            string step = steps.Dequeue();
            var f = typeof(MainForm).GetField(step, BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public);
            if (f?.GetValue(main) is ToolStripItem item) { Log("click " + step); item.PerformClick(); }
            else Log("no menu item " + step);
            nextAt += 2500;
        }
        Environment.Exit(0);
        return 0;
    }

    static void CaptureAll(MainForm main)
    {
        s_shot++;
        var forms = Application.OpenForms.Cast<Form>().ToList();
        if (!forms.Contains(main)) forms.Insert(0, main);
        foreach (Form f in forms)
        {
            if (!f.Visible || f.Width <= 0 || f.Height <= 0) continue;
            try
            {
                string name = $"{s_shot:00}_{f.GetType().Name}.png";
                File.WriteAllBytes(Path.Combine(s_out, name), HeadlessRenderer.CapturePng(f, f.Width, f.Height));
                File.WriteAllText(Path.Combine(s_out, Path.ChangeExtension(name, ".txt")), ControlDump.Dump(f));
                Log($"captured {name} {f.Width}x{f.Height} '{f.Text}'");
            }
            catch (Exception e) { Log($"capture {f.GetType().Name} failed: {e.Message}"); }
        }
    }
}
