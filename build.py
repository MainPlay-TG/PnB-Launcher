import os
import platform
import sys
import yaml
from MainShortcuts2 import ms
from pip._internal.cli.main import main as pip_run
from PyInstaller.__main__ import run as pyi_run
from shutil import make_archive
NAME="PnB-LauncherInstaller"
VERSION="1.3"
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
def pack_release(dir:str,name:str):
  os.symlink(os.path.abspath(dir),"release/"+name)
  return make_archive("release/"+name,"zip","release",name)
@ms.utils.main_func(__name__)
def main():
  log("Building %s %s to source code and executable file %s %s",NAME,VERSION,sys.platform,platform.machine())
  ms.path.cwd(ms.MAIN_DIR)
  log("Installing requirements")
  pip_run(["install","-U","-r","src/requirements.txt"])
  log("Creating dirs")
  clear_dir("dist")
  clear_dir("release")
  log("Creating source release")
  rel_src=pack_release("src","%s_%s-src"%(NAME,VERSION))
  log("Release with source saved to %s",rel_src)
  log("Compiling executable for %s %s",sys.platform,platform.machine())
  pyi_run(["--console","--distpath","dist","--name",NAME,"--onedir","src/__main__.py"])
  log("Creating executable release")
  rel_exe=pack_release("dist/"+NAME,"%s_%s-%s"%(NAME,VERSION,sys.platform))
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
