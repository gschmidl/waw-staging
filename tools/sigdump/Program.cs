// Prints every MainSearch signature (and memory guesses) defined in WhereAreWe.exe.
using System;
using System.Linq;
using System.Reflection;
using System.Text;

static class Program
{
    static string Show(byte[] b) => Convert.ToBase64String(b) + "  \"" + new string(b.Select(c => c >= 32 && c < 127 ? (char)c : '.').ToArray()) + "\"";

    static void Main()
    {
        var asm = typeof(WhereAreWe.GameNames).Assembly;
        foreach (var t in asm.GetTypes().OrderBy(t => t.FullName))
        {
            if (t.IsAbstract && !t.IsSealed) continue;
            foreach (var m in t.GetMembers(BindingFlags.Public | BindingFlags.Static | BindingFlags.Instance | BindingFlags.DeclaredOnly))
            {
                if (m.Name != "MainSearch" && m.Name != "Guesses") continue;
                object target = null;
                bool isStatic = m is FieldInfo fi ? fi.IsStatic : ((PropertyInfo)m).GetGetMethod().IsStatic;
                if (!isStatic)
                {
                    if (typeof(WhereAreWe.MemoryHacker).IsAssignableFrom(t)) continue;
                    var ctor = t.GetConstructor(Type.EmptyTypes);
                    if (ctor == null) { Console.WriteLine($"{t.FullName}.{m.Name}: no default ctor"); continue; }
                    target = ctor.Invoke(null);
                }
                object v; try { v = m is FieldInfo f ? f.GetValue(target) : ((PropertyInfo)m).GetValue(target); } catch (Exception e) { Console.WriteLine($"ERR {t.FullName}.{m.Name}: {(e.InnerException ?? e).Message}"); continue; }
                if (v is byte[] bytes) Console.WriteLine($"SIG {t.FullName} {Show(bytes)}");
                else if (v is Array arr)
                    Console.WriteLine($"GUESS {t.FullName} " + string.Join(" ", arr.Cast<object>().Select(g => { var gt = g.GetType(); var fl = gt.GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance); return "(" + string.Join(",", fl.Select(x => x.GetValue(g))) + ")"; })));
            }
        }
    }
}
