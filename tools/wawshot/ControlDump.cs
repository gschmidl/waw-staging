// Text dump of a window's control tree (bounds, docking, split positions, list columns), written next to each
// capture by both harnesses so the WinForms and Majorsilence layouts can be diffed line by line.
using System.Linq;
using System.Text;
#if MAJORSILENCE_FORMS
using Majorsilence.Forms;
#else
using System.Windows.Forms;
#endif

static class ControlDump
{
    public static string Dump(Form form)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"{form.GetType().Name} size {form.Width}x{form.Height} client {form.ClientSize.Width}x{form.ClientSize.Height}");
        foreach (Control c in form.Controls)
            Dump(c, "", sb);
        return sb.ToString();
    }

    static void Dump(Control c, string path, StringBuilder sb)
    {
        string p = path + "/" + (string.IsNullOrEmpty(c.Name) ? c.GetType().Name : c.Name);
        var b = c.Bounds;
        sb.Append($"{p} {c.GetType().Name} {b.X},{b.Y} {b.Width}x{b.Height} dock={c.Dock}");
        if (!c.Visible) sb.Append(" hidden");
        if (c is SplitContainer sc)
            sb.Append($" split={sc.SplitterDistance} {sc.Orientation} fixed={sc.FixedPanel} min={sc.Panel1MinSize}/{sc.Panel2MinSize} sw={sc.SplitterWidth}");
        if (c is ListView lv)
            sb.Append(" cols=" + string.Join("|", lv.Columns.Cast<ColumnHeader>().Select(h => $"{h.Text}:{h.Width}@{h.DisplayIndex}")));
        sb.AppendLine();
        foreach (Control ch in c.Controls)
            Dump(ch, p, sb);
    }
}
