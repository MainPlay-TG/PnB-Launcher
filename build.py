import os
import sys
import yaml
from MainShortcuts2 import ms
from pip._internal.cli.main import main as pip_run
from PyInstaller.__main__ import run as pyi_run
from shutil import make_archive
NAME="PnB-LauncherInstaller"
VERSION="1.1"
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
  log("Сборка %s %s в исходный код и исполняемый файл %s",NAME,VERSION,sys.platform)
  ms.path.cwd(ms.MAIN_DIR)
  log("Установка зависимостей")
  pip_run(["install","-U","-r","src/requirements.txt"])
  log("Подготовка папок")
  clear_dir("dist")
  clear_dir("release")
  log("Упаковка исходного кода")
  rel_src=pack_release("src","%s_%s-src"%(NAME,VERSION))
  log("Релиз с исходным кодом сохранён в %s",rel_src)
  log("Компиляция релиза для %s",sys.platform)
  pyi_run(["--console","--distpath","dist","--name",NAME,"--onedir","src/__main__.py"])
  log("Упаковка исполняемых файлов")
  rel_exe=pack_release("dist/"+NAME,"%s_%s-%s"%(NAME,VERSION,sys.platform))
  log("Релиз для %s сохранён в %s",sys.platform,rel_exe)
  yml={}
  yml["full_name"]="%s_%s"%(NAME,VERSION)
  yml["name"]=NAME
  yml["platform"]=sys.platform
  yml["release_exe"]=rel_exe
  yml["release_src"]=rel_src
  yml["version"]=VERSION
  ms.file.write("release.yml",yaml.dump(yml))