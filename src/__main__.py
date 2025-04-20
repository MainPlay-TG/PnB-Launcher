import hashlib
import os
import shlex
import shutil
import subprocess
import sys
from traceback import print_exception
from urllib.parse import urlparse,ParseResult
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
ARCH_TYPE="x64"
JDK_URL="https://pnb-launcher.mainplay-tg.ru/jdk.json"
LAUNCHER_DIR=os.path.expanduser("~/%s/MainPlay_TG/Paws'n'Blocks"%("AppData/Local" if sys.platform=="win32" else ".local/share"))
JAVA_BIN=LAUNCHER_DIR+"/launcher-jdk/java"
LAUNCHER_JAR=LAUNCHER_DIR+"/Launcher.jar"
LAUNCHER_URL="https://pnb-launcher.mainplay-tg.ru/Launcher.jar"
OS_TYPE={"win32":"win"}.get(sys.platform,sys.platform)
OS_ARCH_STR="%s/%s"%(OS_TYPE,ARCH_TYPE)
if OS_TYPE=="win":
  JAVA_BIN=JAVA_BIN.replace("/","\\")+".exe"
  LAUNCHER_JAR=LAUNCHER_JAR.replace("/","\\")
def log(text:str,*values,**kw):
  kw.setdefault("file",sys.stderr)
  if len(values)==0:
    return print(text,**kw)
  if len(values)==1:
    values=values[0]
  print(text%values,**kw)
class RemoteFileInfo:
  def __init__(self,raw:dict):
    url_parts:ParseResult=urlparse(raw["url"])
    filename=url_parts.path.split("/")[-1]
    self.path=ms.path.Path(LAUNCHER_DIR+"/launcher-jdk/"+filename,False)
    self.raw:dict=raw
    self.sha512:str=raw["sha512"]
    self.size:int=raw["size"]
    self.url:str=raw["url"]
  def download(self,**kw):
    log("Скачивание файла %s",self.path.full_name)
    kw["path"]=self.path
    kw["url"]=self.url
    ms.dir.create(self.path.parent_dir)
    @ms.utils.decorators.setitem(kw,"cb_progress")
    def _(f,resp,size:int):
      if size>self.size:
        raise Exception("File size does not match",kw["path"])
    ms.utils.download_file(**kw)
    self.check()
    self.unpack()
  def check(self):
    log("Проверка файла %s",self.path.full_name)
    if self.path.size!=self.size:
      self.path.delete()
      raise Exception("File size does not match",self.path)
    with open(self.path,"rb") as f:
      hash=hashlib.sha512()
      for i in f:
        hash.update(i)
    if hash.hexdigest()!=self.sha512:
      self.path.delete()
      raise Exception("File sha512 does not match",self.path)
  def unpack(self):
    log("Распаковка файла %s",self.path.full_name)
    shutil.unpack_archive(self.path,self.path.parent_dir)
    self.path.delete()
def check_launcher_updates(http:requests.Session):
  if not ms.path.exists(LAUNCHER_JAR):
    return True
  ms2hash=http.get(LAUNCHER_URL+".MS2_hash").json()
  if ms2hash["file"]["size"]!=os.path.getsize(LAUNCHER_JAR):
    return True
  hash:hashlib._Hash=getattr(hashlib,ms2hash["hash"]["type"])()
  with open(LAUNCHER_JAR,"rb") as f:
    for chunk in f:
      hash.update(chunk)
  return ms2hash["hash"]["hex"]!=hash.hexdigest()
@ms.utils.main_func(__name__)
def main(**kw):
  log("Папка лаунчера: %s",LAUNCHER_DIR)
  with requests.Session() as http:
    kw["method"]="GET"
    kw["session"]=http
    try:
      if check_launcher_updates(http):
        log("Скачивание лаунчера")
        ms.path.delete(LAUNCHER_JAR)
        ms.utils.download_file(LAUNCHER_URL,LAUNCHER_JAR,**kw)
      if not ms.path.exists(JAVA_BIN):
        log("Получение списка JDK")
        jdk_list:dict[str,dict]=ms.utils.request(url=JDK_URL,**kw).json()
        if not OS_ARCH_STR in jdk_list:
          return log("JDK для %s отсутствует, запустите лаунчер вручную, используя сторонний JDK 17+",OS_ARCH_STR)
        jdk=RemoteFileInfo(jdk_list[OS_ARCH_STR]["jdk"])
        jfx=RemoteFileInfo(jdk_list[OS_ARCH_STR]["javafx"])
        jdk.download(**kw)
        jfx.download(**kw)
        jdk_mods=LAUNCHER_DIR+"/launcher-jdk/"+jdk.raw["jmods_dir"]
        jfx_mods=LAUNCHER_DIR+"/launcher-jdk/"+jfx.raw["jmods_dir"]
        log("Установка JavaFX")
        for jmod in ms.dir.list(jfx_mods,exts=["jmod"],type="file"):
          jmod.move(jdk_mods+"/"+jmod.full_name)
        ms.path.delete(jfx_mods)
        ms.path.link(LAUNCHER_DIR+"/launcher-jdk/"+jdk.raw["executable"],JAVA_BIN)
    except requests.ConnectionError as exc:
      log("Не удалось соединиться с сервером. Проверьте подключение к интернету и попробуйте снова. Если проблема повторяется, спросите в чате https://t.me/PawsNBlocks/1")
      print_exception(exc)
      return 1
  ssn={"linux":"start.sh","win":"start.bat"}.get(OS_TYPE)
  if ssn:
    ssp=LAUNCHER_DIR+"/"+ssn
    if OS_TYPE=="win":
      if ms.path.exists(ssp):
        if "/launcher-jdk/" in ms.file.read(ssp):
          ms.path.delete(ssp)
    if not ms.path.exists(ssp):
      log("Запись скрипта %s",ssn)
      sst=("#!/bin/env bash\n" if OS_TYPE=="linux" else "")+shlex.join([JAVA_BIN,"-jar",LAUNCHER_JAR])
      ms.file.write(ssp,sst)
  subprocess.call([JAVA_BIN,"-jar",LAUNCHER_JAR])