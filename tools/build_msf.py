"""Build the cross-platform (Majorsilence.Forms / Avalonia) variant of the Where Are We? port.

    python tools/build_msf.py [--src work] [--out build/msf] [--rid win-x64|linux-x64|osx-arm64|...] [--publish]

Copies the port's WinForms source, converts it with the pinned Majorsilence migrator (namespace rewrite),
fixes the fully-qualified System.Drawing names the migrator leaves, and builds net10.0 with
MAJORSILENCE_FORMS defined.
"""
import argparse
import os
import shutil
import subprocess
import sys

MSF_VERSION = '26.8.2'
HERE = os.path.dirname(os.path.abspath(__file__))

CSPROJ = '''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <AssemblyName>WhereAreWe</AssemblyName>
    <GenerateAssemblyInfo>False</GenerateAssemblyInfo>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net10.0-windows</TargetFramework>
    <UseWindowsForms>True</UseWindowsForms>
    <LangVersion>14.0</LangVersion>
    <AllowUnsafeBlocks>True</AllowUnsafeBlocks>
    <CheckForOverflowUnderflow>False</CheckForOverflowUnderflow>
    <RootNamespace />
    <ApplicationIcon>app.ico</ApplicationIcon>
    <GenerateResourceUsePreserializedResources>true</GenerateResourceUsePreserializedResources>
    <DefineConstants>$(DefineConstants);MAJORSILENCE_FORMS</DefineConstants>
    <NoWarn>$(NoWarn);CS0618;CS0612;CS0169;CS0414;CS0649;CS0067;CS0108;CS0114;CS0162;CS0168;CS0219;CS1998;CA1416;SYSLIB0011;SYSLIB0014;SYSLIB0050;SYSLIB0051;NU1701</NoWarn>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="System.Resources.Extensions" Version="10.0.0" />
    <PackageReference Include="System.Configuration.ConfigurationManager" Version="10.0.0" />
    <PackageReference Include="System.Diagnostics.PerformanceCounter" Version="10.0.0" />
  </ItemGroup>
</Project>
'''


def replace_in_sources(root, pairs, what):
    n = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('bin', 'obj')]
        for f in files:
            if f.endswith('.cs'):
                p = os.path.join(dirpath, f)
                s = open(p, encoding='utf-8-sig').read()
                t = s
                for old, new in pairs:
                    t = t.replace(old, new)
                if t != s:
                    open(p, 'w', encoding='utf-8').write(t)
                    n += 1
    print(what, 'in', n, 'files')


def msf_invoke_workaround(root):
    """Majorsilence.Forms 26.8.2: Control.Invoke(Delegate) recurses forever for a MethodInvoker (it calls
    Invoke(method2), which binds to itself). Pass Actions instead, which it hands to the backend."""
    replace_in_sources(root, [('(MethodInvoker)delegate', '(System.Action)delegate'),
                              ('new MethodInvoker(', 'new System.Action(')], 'MethodInvoker -> Action')


def msf_split_containers(root):
    """Majorsilence.Forms 26.8.2 rescales a split from its previous size, so clamps at transient sizes stick;
    WhereAreWe.WinFormsSplitContainer (work/Staging) keeps WinForms' rule. Use it for the designer's plain ones."""
    replace_in_sources(root, [('new Majorsilence.Forms.SplitContainer()', 'new WhereAreWe.WinFormsSplitContainer()')],
                       'SplitContainer -> WinFormsSplitContainer')


def run(cmd, cwd=None):
    print('>', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=os.path.join(HERE, '..', 'work'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'build', 'msf'))
    ap.add_argument('--rid', default=None, help='runtime identifier for --publish (default: current OS)')
    ap.add_argument('--publish', action='store_true', help='self-contained single folder via dotnet publish')
    ap.add_argument('--configuration', default='Release')
    a = ap.parse_args()
    src, out = os.path.abspath(a.src), os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    for entry in os.listdir(out):  # clear the contents, keep the folder (build servers may hold it open)
        path = os.path.join(out, entry)
        shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns('bin', 'obj', '.git', '.gitignore', '*.csproj'), dirs_exist_ok=True)
    with open(os.path.join(out, 'WhereAreWe.csproj'), 'w', encoding='utf-8') as f:
        f.write(CSPROJ)
    run(['majorsilence-migrate', 'WhereAreWe.csproj', '--no-backup', '--no-report', '--package-version', MSF_VERSION], cwd=out)
    run([sys.executable, '-I', os.path.join(HERE, 'fqdraw.py'), out])
    run([sys.executable, '-I', os.path.join(HERE, 'adddrawusing.py'), out])
    msf_invoke_workaround(out)
    msf_split_containers(out)
    if a.publish:
        cmd = ['dotnet', 'publish', '-c', a.configuration, '--self-contained', 'true', '-nologo']
        if a.rid:
            cmd += ['-r', a.rid]
        run(cmd, cwd=out)
    else:
        run(['dotnet', 'build', '-c', a.configuration, '-nologo'], cwd=out)


if __name__ == '__main__':
    main()
