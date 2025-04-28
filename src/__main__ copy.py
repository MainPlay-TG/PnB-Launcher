import hashlib
import os
import platform
import shlex
import shutil
import sqlite3
import subprocess
import sys
from traceback import print_exception
try:
  import requests
  from MainShortcuts2 import ms
except Exception:
  import subprocess
  print("У вас не установлены необходимые библиотеки, придётся немного подождать",file=sys.stderr)
  subprocess.call([sys.executable,"-m","pip","install","-U","requests","MainShortcuts2"])
  import requests
  from MainShortcuts2 import ms
try:
  ms.utils.main_func
except Exception:
  print("MainShortcuts2 устарел, обновляю",file=sys.stderr)
  subprocess.call([sys.executable,"-m","pip","install","-U","MainShortcuts2"])
  print("Перезапустите программу",file=sys.stderr)
  sys.exit(1)
def detect_platform():
  at=platform.machine().lower()
  ot=sys.platform.lower()
  at={"x86_64":"amd64"}.get(at,at)
  ot={"win32":"windows"}.get(ot,ot)
  return at,ot
ARCH_TYPE,OS_TYPE=detect_platform()
LAUNCHER_DIR=os.path.expanduser("~/%s/MainPlay_TG/Paws'n'Blocks"%("AppData/Local" if sys.platform=="win32" else ".local/share"))
JAVA_BIN=LAUNCHER_DIR+"/launcher-java/bin/java"
JAVA_DIR=LAUNCHER_DIR+"/launcher-java"
LAUNCHER_JAR=LAUNCHER_DIR+"/Launcher.jar"
LAUNCHER_URL="https://pnb-launcher.mainplay-tg.ru/Launcher.jar"
if OS_TYPE=="windows":
  JAVA_BIN=JAVA_BIN.replace("/","\\")+".exe"
  LAUNCHER_JAR=LAUNCHER_JAR.replace("/","\\")
def log(text:str,*values,**kw):
  kw.setdefault("file",sys.stderr)
  if len(values)==0:
    return print(text,**kw)
  if len(values)==1:
    values=values[0]
  print(text%values,**kw)
class JavaDownloader(ms.ObjectBase):
  def __init__(self,dev:str,version:int,type:str):
    self.arch=ARCH_TYPE
    self.dev=dev
    self.installed=False
    self.platform=OS_TYPE
    self.tmp_dir=tmp_dir=LAUNCHER_DIR+"/downloading-java/"
    self.type=type
    self.version=version
  def __exit__(self,*a):
    ms.path.delete(LAUNCHER_DIR+"/downloading-java")
  def check(self):
    if not ms.path.exists(JAVA_BIN):
      return False
    if not ms.path.exists(JAVA_DIR+"/version.json"):
      return False
    data=ms.json.read(JAVA_DIR+"/version.json")
    for i in ("arch","dev","platform","type","version"):
      if data[i]!=getattr(self,i):
        return False
    self.installed=True
    return True
  def download(self):
    mkdir_clear(self.tmp_dir)
    ms.utils.download_file("https://mainplay-tg.ru/files/runtime.db",tmp_dir+"/runtime.db")
  def install(self):
    mkdir_clear(JAVA_DIR)
    ms.json.write(JAVA_DIR+"/version.json",{i:getattr(self,i) for i in ("arch","dev","platform","type","version")})
    self.installed=True
  def delete_old(self):
    if ms.path.exists(LAUNCHER_DIR+"/launcher-jdk"):
      log("Удаление старой JDK")
      ms.path.delete(LAUNCHER_DIR+"/launcher-jdk")
    if ms.path.exists(LAUNCHER_DIR+"/launcher-jre"):
      log("Удаление старой JRE")
      ms.path.delete(LAUNCHER_DIR+"/launcher-jre")
  def run_all(self):
    with self:
      self.delete_old()
      if not self.check():
        self.download()
        self.install()
def install_java(*,_try_again=True):

  for i in ms.dir.list_iter(JAVA_DIR):
    i.delete()
  tmp_dir=LAUNCHER_DIR+"/downloading-java/"
  with ms.path.TempFiles(tmp_dir) as temp:
    ms.dir.create(tmp_dir)
    for i in ms.dir.list_iter(tmp_dir):
      i.delete()
    
    with sqlite3.connect(tmp_dir+"/runtime.db") as conn:
      cur=conn.cursor()
      cur.execute("SELECT tags,url FROM java WHERE arch=? AND developer=? AND filetype='archive' AND platform=? AND type=? AND version=?;",(ARCH_TYPE,ver_data["developer"],OS_TYPE,ver_data["type"],ver_data["version"]))
      sel:list[tuple[str,str]]=cur.fetchall()
      if len(sel)==0:
        log("Не удалось найти подходящую Java для %s %s",OS_TYPE,ARCH_TYPE)
        return False
      for _tags,url in sel:
        tags:list[str]=ms.json.decode(_tags)
        if "full" in tags:
          if not "musl" in tags:
            log("Выбрана %(developer)s %(type)s %(version)s Full для %(platform)s %(arch)s",ver_data)
            cur.execute("SELECT filename,filesize,sha1 FROM fileinfo WHERE url=?;",(url,))
            sel2:list[tuple[str,int,str]]=cur.fetchall()
            filename,filesize,sha1=sel2[0]
            log("Скачивание Java")
            ms.utils.download_file(url,tmp_dir+filename)
            log("Проверка целостности Java")
            if os.path.getsize(tmp_dir+filename)!=filesize:
              log("Файл повреждён!")
              if _try_again:
                log("Повторная попытка")
                temp.remove_files()
                return install_java(_try_again=False)
              return False
            with open(tmp_dir+filename,"rb") as f:
              sha1h=hashlib.sha1()
              for i in f:
                sha1h.update(i)
            if sha1!=sha1h.hexdigest():
              log("Файл повреждён!")
              if _try_again:
                log("Повторная попытка")
                temp.remove_files()
                return install_java(_try_again=False)
              return False
            log("Распаковка Java")
            shutil.unpack_archive(tmp_dir+filename,tmp_dir)
            log("Установка Java")
            for i in ms.dir.list_iter(ms.dir.list(tmp_dir,type="dir")[0]):
              i.move(JAVA_DIR+"/"+i.full_name)
            log("Java успешно установлена")
            ms.json.write(JAVA_DIR+"/version.json",ver_data)
            return True
  log("Не удалось найти подходящую Java для %s %s",OS_TYPE,ARCH_TYPE)
  return False
def mkdir_clear(path:str):
  ms.dir.create(path)
  for i in ms.dir.list_iter(path):
    i.delete()
def check_launcher_updates():
  if not ms.path.exists(LAUNCHER_JAR):
    return True
  ms2hash=ms.utils.request("GET",LAUNCHER_URL+".MS2_hash").json()
  if ms2hash["file"]["size"]!=os.path.getsize(LAUNCHER_JAR):
    return True
  hash:hashlib._Hash=getattr(hashlib,ms2hash["hash"]["type"])()
  with open(LAUNCHER_JAR,"rb") as f:
    for chunk in f:
      hash.update(chunk)
  return ms2hash["hash"]["hex"]!=hash.hexdigest()
def handle_main_exc(func):
  def wrapper():
    try:
      result=func()
    except Exception as exc:
      print_exception(exc)
      result=1
    if result:
      input("Нажмите Enter чтобы закрыть окно")
    return result
  return wrapper
@ms.utils.main_func(__name__)
@handle_main_exc
def main():
  log("Папка лаунчера: %s",LAUNCHER_DIR)
  ms.dir.create(LAUNCHER_DIR)
  try:
    if check_launcher_updates():
      log("Скачивание/обновление лаунчера")
      ms.path.delete(LAUNCHER_JAR)
      ms.utils.download_file(LAUNCHER_URL,LAUNCHER_JAR)
    launcher_jar=os.path.realpath(LAUNCHER_JAR)
    if install_java():
      java_bin=os.path.realpath(JAVA_BIN)
      log("Используется встроенная Java")
    else:
      log("Не удалось установить JRE, попробую использовать системную Java")
      java_bin="java"
  except requests.ConnectionError as exc:
    log("Не удалось соединиться с сервером. Проверьте подключение к интернету и попробуйте снова. Если проблема повторяется, спросите в чате https://t.me/PawsNBlocks/1")
    print_exception(exc)
    return 1
  ssn={"linux":"start.sh","win":"start.bat"}.get(OS_TYPE)
  if ssn:
    ssp=LAUNCHER_DIR+"/"+ssn
    if ms.path.exists(ssp):
      if "launcher-jdk" in ms.file.read(ssp):
        ms.path.delete(ssp)
    if not ms.path.exists(ssp):
      log("Запись скрипта %s",ssn)
      sst=("#!/bin/env bash\n" if OS_TYPE=="linux" else "")+shlex.join([java_bin,"-jar",launcher_jar])
      ms.file.write(ssp,sst)
  log("Запуск лаунчера")
  return subprocess.call([java_bin,"-jar",launcher_jar])
