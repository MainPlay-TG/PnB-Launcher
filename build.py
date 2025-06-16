import os
import platform
import sys
import yaml
from MainShortcuts2 import ms
from pip._internal.cli.main import main as pip_run
from PyInstaller.__main__ import run as pyi_run
from shutil import make_archive
NAME="PnB-LauncherInstaller"
VERSION="2.0"
def log(text:str,*values,**kw):
  if len(values)==1:
    text=text%values[0]
  if len(values)>1:
    text=text%values
  kw.setdefault("file",sys.stderr)
  print(text,**kw)
def clear_dir(dir:str):
  ms.dir.create(dir)
  for i in ms.dir.list(dir):
    i.delete()
def edit_source():
  import_lines=[]
  is_import=False
  new_lines=[]
  old_lines=[i.rstrip() for i in ms.file.read("src/__main__.py").split("\n")]
  for line in old_lines:
    if line.startswith("NAME="):
      line="NAME=%r"%NAME
    if line.startswith("VERSION="):
      line="VERSION=%r"%VERSION
    if line.startswith("# IMPORTS.START"):
      is_import=True
    if line.startswith("# IMPORTS.END"):
      new_lines.append("try:")
      for i in import_lines:
        new_lines.append("  %s"%i)
      new_lines.append("except Exception:")
      new_lines.append("  import subprocess")
      new_lines.append("  REQIREMENTS_DATA=%r"%ms.file.read("src/requirements.txt"))
      new_lines.append("  REQIREMENTS_PATH=__file__+'.requirements.txt'")
      new_lines.append("  with open(REQIREMENTS_PATH,'w') as f:")
      new_lines.append("    f.write(REQIREMENTS_DATA)")
      new_lines.append("  subprocess.call(['pip','install','-U','-r',REQIREMENTS_PATH])")
      for i in import_lines:
        new_lines.append("  %s"%i)
      import_lines.clear()
      is_import=False
    if not line.lstrip().startswith("#"):
      if is_import:
        import_lines.append(line)
      else:
        new_lines.append(line)
  if is_import:
    raise Exception("Unfinished IMPORTS")
  ms.file.write("src/__main__.py","\n".join(new_lines))
@ms.utils.main_func(__name__)
def main():
  log("Building %s %s to source code and executable file %s %s",NAME,VERSION,sys.platform,platform.machine())
  ms.path.cwd(ms.MAIN_DIR)
  log("Installing requirements")
  pip_run(["install","-U","-r","src/requirements.txt"])
  log("Creating dirs")
  clear_dir("dist")
  clear_dir("release")
  log("Editing source")
  edit_source()
  log("Creating source release")
  rel_src="release/%s_%s-src.py"%(NAME,VERSION)
  ms.file.copy("src/__main__.py",rel_src)
  log("Release with source saved to %s",rel_src)
  log("Compiling executable for %s %s",sys.platform,platform.machine())
  pyi_run(["--console","--distpath","dist","--name",NAME,"--onefile","src/__main__.py"])
  log("Creating executable release")
  rel_exe="release/%s_%s-%s.exe"%(NAME,VERSION,sys.platform)
  ms.file.move(ms.dir.list("dist",exts=["exe"])[0],rel_exe)
  log("Release for %s saved to %s",sys.platform,rel_exe)
  yml={}
  yml["full_name"]="%s_%s"%(NAME,VERSION)
  yml["name"]=NAME
  yml["platform"]=sys.platform
  yml["release_exe"]=rel_exe
  yml["release_src"]=rel_src
  yml["version"]=VERSION
  ms.file.write("release.yml",yaml.dump(yml))
  log("Complete!")
