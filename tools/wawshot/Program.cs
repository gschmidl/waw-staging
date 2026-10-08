// Runs Where Are We?'s MainForm in-process and saves every open form as a PNG (Control.DrawToBitmap),
// optionally after clicking menu items. Meant to run on a private desktop (tools/run_hidden.py).
//   WAWSHOT_OUT     output folder (default .)
//   WAWSHOT_API     DOSBox Staging API host:port
//   WAWSHOT_DELAY   ms before the first capture (default 4000)
//   WAWSHOT_STEPS   ;-separated MainForm menu item fields to click, each followed by a capture
// Command-line arguments go to Where Are We? itself (e.g. -g mm1).
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Windows.Forms;
using WhereAreWe;

static class Program
{
    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);
    delegate bool EnumProc(IntPtr hwnd, IntPtr lParam);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool EnumThreadWindows(int threadId, EnumProc proc, IntPtr lParam);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr parent, EnumProc proc, IntPtr lParam);
    [System.Runtime.InteropServices.DllImport("kernel32.dll")] static extern int GetCurrentThreadId();
    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)] static extern int GetClassName(IntPtr h, System.Text.StringBuilder sb, int n);
    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)] static extern int GetWindowText(IntPtr h, System.Text.StringBuilder sb, int n);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool PostMessage(IntPtr h, int msg, IntPtr w, IntPtr l);

    static string ClassOf(IntPtr h) { var sb = new System.Text.StringBuilder(256); GetClassName(h, sb, 256); return sb.ToString(); }
    static string WindowText(IntPtr h) { var sb = new System.Text.StringBuilder(4096); GetWindowText(h, sb, 4096); return sb.ToString(); }
    static List<IntPtr> NativeDialogs()
    {
        var list = new List<IntPtr>();
        EnumThreadWindows(GetCurrentThreadId(), (h, l) => { if (IsWindowVisible(h) && ClassOf(h) == "#32770") list.Add(h); return true; }, IntPtr.Zero);
        return list;
    }
    static List<string> ChildTexts(IntPtr parent)
    {
        var list = new List<string>();
        EnumChildWindows(parent, (h, l) => { string t = WindowText(h); if (t.Length > 0) list.Add(t); return true; }, IntPtr.Zero);
        return list;
    }

    static string s_out;
    static int s_shot;
    static int s_dialogs;
    static readonly List<string> s_log = new List<string>();

    static void Log(string s) { s_log.Add($"{DateTime.Now:HH:mm:ss.fff} {s}"); File.WriteAllLines(Path.Combine(s_out, "wawshot.log"), s_log); }

    [STAThread]
    static int Main()
    {
        s_out = Environment.GetEnvironmentVariable("WAWSHOT_OUT") ?? ".";
        Directory.CreateDirectory(s_out);
        int delay = int.TryParse(Environment.GetEnvironmentVariable("WAWSHOT_DELAY"), out int d) ? d : 4000;
        var steps = new Queue<string>((Environment.GetEnvironmentVariable("WAWSHOT_STEPS") ?? "").Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries));
        Environment.SetEnvironmentVariable("WAW_DOSBOX_API", Environment.GetEnvironmentVariable("WAWSHOT_API"));
        // as WhereAreWe's Program.Main: a WhereAreWe.settings next to the harness makes the settings portable
        PortableSettingsProvider.Configure();
        PortableSettingsProvider.MoveTempFiles();

        var asm = typeof(MainForm).Assembly;
        var st = asm.GetType("WhereAreWe.Properties.Settings");
        var def = st.GetProperty("Default").GetValue(null);
        st.GetProperty("WarnNonAdmin").SetValue(def, false);
        st.GetProperty("WizardRun").SetValue(def, true);

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.ThreadException += (s, e) => Log("ThreadException: " + e.Exception);
        AppDomain.CurrentDomain.UnhandledException += (s, e) => Log("Unhandled: " + e.ExceptionObject);
        var main = new MainForm();
        // Modal dialogs would stop the run: log and capture them, then close them.
        var dismisser = new Timer { Interval = 300 };
        dismisser.Tick += (s, e) =>
        {
            foreach (IntPtr box in NativeDialogs())
            {
                Log("messagebox '" + WindowText(box) + "': " + string.Join(" | ", ChildTexts(box)));
                PostMessage(box, 0x0111, (IntPtr)2, IntPtr.Zero); // WM_COMMAND IDCANCEL
                PostMessage(box, 0x0111, (IntPtr)1, IntPtr.Zero); // WM_COMMAND IDOK
            }
            foreach (Form f in Application.OpenForms.Cast<Form>().ToList())
            {
                if (f == main || !f.Visible || !f.Modal) continue;
                Log($"dialog {f.GetType().Name} '{f.Text}': {string.Join(" | ", f.Controls.Cast<Control>().Where(c => c is Label || c is TextBox).Select(c => c.Text))}");
                try
                {
                    using (var bmp = new Bitmap(f.Width, f.Height))
                    {
                        f.DrawToBitmap(bmp, new Rectangle(0, 0, f.Width, f.Height));
                        bmp.Save(Path.Combine(s_out, $"dialog_{++s_dialogs:00}_{f.GetType().Name}.png"), ImageFormat.Png);
                    }
                }
                catch (Exception) { }
                f.DialogResult = DialogResult.Cancel;
                f.Close();
            }
        };
        dismisser.Start();
        var timer = new Timer { Interval = delay };
        timer.Tick += (s, e) =>
        {
            timer.Interval = 2500;
            CaptureAll();
            if (steps.Count == 0) { timer.Stop(); Application.Exit(); return; }
            string step = steps.Dequeue();
            var f = typeof(MainForm).GetField(step, BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public);
            if (f?.GetValue(main) is ToolStripItem item) { Log("click " + step); item.PerformClick(); }
            else Log("no menu item " + step);
        };
        main.Shown += (s, e) => timer.Start();
        Application.Run(main);
        return 0;
    }

    static void CaptureAll()
    {
        s_shot++;
        foreach (Form f in Application.OpenForms.Cast<Form>().ToList())
        {
            if (!f.Visible || f.Width <= 0 || f.Height <= 0) continue;
            try
            {
                using (var bmp = new Bitmap(f.Width, f.Height))
                {
                    // PrintWindow shows the window as composed; DrawToBitmap paints children in reverse z-order.
                    using (var g = Graphics.FromImage(bmp))
                    {
                        IntPtr hdc = g.GetHdc();
                        bool ok = PrintWindow(f.Handle, hdc, 2);
                        g.ReleaseHdc(hdc);
                        if (!ok) f.DrawToBitmap(bmp, new Rectangle(0, 0, f.Width, f.Height));
                    }
                    string name = $"{s_shot:00}_{f.GetType().Name}.png";
                    bmp.Save(Path.Combine(s_out, name), ImageFormat.Png);
                    File.WriteAllText(Path.Combine(s_out, Path.ChangeExtension(name, ".txt")), ControlDump.Dump(f));
                    Log($"captured {name} {f.Width}x{f.Height} '{f.Text}'");
                }
            }
            catch (Exception e) { Log($"capture {f.GetType().Name} failed: {e.Message}"); }
        }
    }
}
