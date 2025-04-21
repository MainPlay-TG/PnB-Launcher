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
JAVA_BIN=LAUNCHER_DIR+"/launcher-jre/bin/java"
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
def install_java(*,_try_again=True):
  if ms.path.exists(LAUNCHER_DIR+"/launcher-jdk"):
    log("Удаление старой JDK")
    ms.path.delete(LAUNCHER_DIR+"/launcher-jdk")
  if os.path.isfile(os.path.realpath(JAVA_BIN)):
    return True
  ms.dir.create(LAUNCHER_DIR+"/launcher-jre")
  for i in ms.dir.list_iter(LAUNCHER_DIR+"/launcher-jre"):
    i.delete()
  tmp_dir=LAUNCHER_DIR+"/downloading-jre/"
  with ms.path.TempFiles(tmp_dir) as temp:
    ms.dir.create(tmp_dir)
    for i in ms.dir.list_iter(tmp_dir):
      i.delete()
    ms.utils.download_file("https://mainplay-tg.ru/files/runtime.db",tmp_dir+"/runtime.db")
    with sqlite3.connect(tmp_dir+"/runtime.db") as conn:
      cur=conn.cursor()
      cur.execute("SELECT tags,url FROM java WHERE arch=? AND developer='bellsoft' AND filetype='archive' AND platform=? AND type='jre' AND version=23;",(ARCH_TYPE,OS_TYPE))
      sel:list[tuple[str,str]]=cur.fetchall()
      if len(sel)==0:
        log("Не удалось найти подходящую JRE для %s %s",OS_TYPE,ARCH_TYPE)
        return False
      for _tags,url in sel:
        tags:list[str]=ms.json.decode(_tags)
        if "full" in tags:
          if not "musl" in tags:
            log("Выбрана Bellsoft JRE 23 Full для %s %s",OS_TYPE,ARCH_TYPE)
            cur.execute("SELECT filename,filesize,sha1 FROM fileinfo WHERE url=?;",(url,))
            sel2:list[tuple[str,int,str]]=cur.fetchall()
            filename,filesize,sha1=sel2[0]
            log("Скачивание JRE")
            ms.utils.download_file(url,tmp_dir+filename)
            log("Проверка целостности JRE")
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
            log("Распаковка JRE")
            shutil.unpack_archive(tmp_dir+filename,tmp_dir)
            log("Установка JRE")
            for i in ms.dir.list_iter(ms.dir.list(tmp_dir,type="dir")[0]):
              i.move(LAUNCHER_DIR+"/launcher-jre/"+i.full_name)
            log("JRE успешно установлена")
            return True
  log("Не удалось найти подходящую JRE для %s %s",OS_TYPE,ARCH_TYPE)
  return False
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
