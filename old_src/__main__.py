import atexit
import os
import platform
import shutil
import subprocess
import sys
import traceback
from argparse import ArgumentParser
from threading import Thread
# IMPORTS.START
import requests
from MainShortcuts2 import ms
from MainShortcuts2.advanced import _Platform
from MainShortcuts2.ms2hash import Format1
from MainShortcuts2.sql.sqlite import Database
# IMPORTS.END
NAME="AUTO"
VERSION="AUTO"
argp=ArgumentParser()
argp.add_argument("--debug",action="store_true")
argp.add_argument("--dev",action="store_true")
argp.add_argument("--stacktrace",action="store_true")
class LauncherInstaller(ms.ObjectBase):
  ROOT_URL="https://pnb-launcher.mainplay-tg.ru/"
  class JavaVersion(ms.ObjectBase):
    def __init__(self,inst,raw):
      self._url=None
      self.id:int=raw["id"]
      self.inst:LauncherInstaller=inst
      self.raw=raw
      self.tags:list[str]=[ms.json.encode(i) for i in raw["tags"]]
      self.type:str=raw["type"]
      self.version:int=raw["version"]
    @property
    def dir(self)->str:
      return self.inst.java_dir+"/"+self.id
    @property
    def executable(self)->str:
      result=self.dir+"/bin/java"
      if self.inst.platform.is_windows:
        result+=".exe"
      return result
    @property
    def db_index(self):
      return {"arch":self.inst.arch,"developer":"bellsoft","platform":self.inst.system,"type":self.type,"version":self.version}
    @property
    def url(self):
      def find(index):
        sel=self.inst.runtime_db.select("java",["developer","tags","url"],index)
        for developer,tags,url in sel:
          for tag in self.tags:
            if not tag in tags:
              continue
            return developer,url
        return None,None
      if self._url is None:
        index=self.db_index
        self.developer,self._url=find(index)
        if self._url is None:
          self.inst.update_runtime_db()
          self.developer,self._url=find(index)
        if self._url is None:
          index.pop("developer",None)
          self.developer,self._url=find(index)
        if self._url is None:
          raise ValueError("Не удалось найти подходящую версию Java")
      return self._url
    def install(self):
      if ms.path.exists(self.executable):
        return print("Java %s установлена"%self.id)
      ms.path.delete(self.dir)
      sel:tuple[str,int,str]=self.inst.runtime_db.select("fileinfo",["filename","filesize","sha1"],{"url":self.url})[0]
      filename,filesize,sha1=sel
      dest_file=ms.path.Path(self.inst.java_dir+"/"+filename)
      print("Скачивание %s"%filename)
      with ms.path.TempFiles(dest_file) as temp:
        try:
          self.inst.downloader.download2file(self.url,dest_file,resume=True)
        except KeyboardInterrupt:
          temp.files.clear()
          raise KeyboardInterrupt("Скачивание прервано")
        print("Проверка целостности %s"%filename)
        local=Format1.generate(dest_file,True,hash_type="sha1")
        if local.file_size!=filesize:
          raise RuntimeError("Скачанный файл повреждён")
        if local.hash_hex!=sha1:
          raise RuntimeError("Скачанный файл повреждён")
        print("Распаковка %s"%filename)
        dest_dir=ms.path.Path("%s/.install-%s"%(self.inst.java_dir,self.id))
        temp.add(dest_dir)
        shutil.unpack_archive(dest_file,dest_dir)
        print("Установка Java %s"%self.id)
        ms.dir.list(dest_dir,type="dir")[0].move(self.dir)
      print("Java %s успешно установлена"%self.id)
      info=self.db_index
      info.update(self.raw)
      info["developer"]=self.developer
      ms.json.write(self.dir+"/version.json",info)
    def install_background(self):
      if ms.path.exists(self.executable):
        return print("Java %s установлена"%self.id)
      print("Java %s будет установлена в фоне и станет доступна при следующем запуске"%self.id)
      thread=Thread(target=self.install)
      thread.start()
      self.inst.threads.append(thread)
  def __init__(self):
    self._arch=None
    self._dir=None
    self._downloader=None
    self._java_dir=None
    self._platform=None
    self._runtime_db=None
    self._system=None
    self.self_update()
    self.move_old_launcher()
    self.threads:list[Thread]=[]
  @property
  def arch(self) -> str:
    if self._arch is None:
      self._arch=platform.machine().lower()
      self._arch={"x86_64":"amd64"}.get(self._arch,self._arch)
    return self._arch
  @property
  def dir(self)->str:
    if self._dir is None:
      self._dir=os.path.expanduser("~/%s/MainPlay_TG/PawsNBlocks"%("AppData/Local" if self.platform.is_windows else ".local/share"))
      ms.dir.create(self._dir+"/updates")
    return self._dir
  @property
  def downloader(self):
    if self._downloader is None:
      self._downloader=ms.advanced.FileDownloader()
      try:
        import progressbar
        self._downloader.h_progressbar()
      except Exception:
        print("Не удалось создать прогрессбар при скачивании")
    return self._downloader
  @property
  def java_dir(self) -> str:
    if self._java_dir is None:
      self._java_dir=self.dir+"/java/%s-%s"%(self.system,self.arch)
      ms.dir.create(self._java_dir)
    return self._java_dir
  @property
  def platform(self)->_Platform:
    if self._platform is None:
      self._platform=ms.advanced.get_platform()
    return self._platform
  @property
  def runtime_db(self)->Database:
    if self._runtime_db is None:
      if not ms.path.exists(self.dir+"/runtime.db"):
        self.update_runtime_db()
      self._runtime_db=Database(self.dir+"/runtime.db",autosave=False)
    if self._runtime_db.closed:
      self._runtime_db=None
      return self.runtime_db
    return self._runtime_db
  @property
  def system(self) -> str:
    if self._system is None:
      self._system=sys.platform.lower()
      self._system={"win32":"windows"}.get(self._system,self._system)
    return self._system
  def update_runtime_db(self):
    if not self._runtime_db is None:
      self.runtime_db.close()
      self._runtime_db=None
    ms.utils.download_file("https://mainplay-tg.ru/files/runtime.db",self.dir+"/runtime.db")
  def move_old_launcher(self):
    old_dir=os.path.expanduser("~/%s/MainPlay_TG/Paws'n'Blocks"%("AppData/Local" if self.platform.is_windows else ".local/share"))
    if not ms.path.exists(old_dir):
      return
    print("Перемещаю файлы старого лаунчера...")
    ms.path.delete(old_dir+"/downloading-java")
    ms.path.delete(old_dir+"/launcher-java")
    ms.path.delete(old_dir+"/launcher-jdk")
    ms.path.delete(old_dir+"/launcher-jre")
    ms.path.delete(old_dir+"/Launcher.jar")
    for i in ms.dir.list_iter(old_dir,type="file"):
      print("- %s"%i.full_name)
      dest=self.dir+"/"+i.full_name
      if ms.path.exists(dest):
        print("Не удалось переместить файл %s т. к. он уже существует"%i.full_name)
      else:
        i.move(dest)
    if ms.path.exists(old_dir+"/updates"):
      for i in ms.dir.list_iter(old_dir+"/updates"):
        dest=self.dir+"/updates/"+i.full_name
        if ms.path.exists(dest):
          print("Не удалось переместить модпак %s т. к. он уже существует"%i.full_name)
        else:
          i.move(dest)
      if len(ms.dir.list(old_dir+"/updates"))==0:
        ms.path.delete(old_dir+"/updates")
    if len(ms.dir.list(old_dir))==0:
      ms.path.delete(old_dir)
  def self_update(self):
    GH_REPO="MainPlay-TG","PnB-Launcher"
    new_version=None
    for line in ms.utils.request("GET","https://github.com/%s/%s/raw/refs/heads/master/build.py"%GH_REPO).text.split("\n"):
      if line.startswith("VERSION="):
        new_version=eval(line[len("VERSION="):])
        break
    if new_version is None:
      return
    if VERSION==new_version:
      return
    print("Обновление престартера (%s -> %s)"%(VERSION,new_version))
    release_info=ms.utils.request("GET","https://api.github.com/repos/%s/%s/releases/latest"%GH_REPO).json()
    assets=release_info["assets"]
    ext=ms.path.Path(ms.MAIN_FILE).ext
    for asset in assets:
      if asset["name"].startswith(NAME):
        if asset["name"].endswith(ext):
          print("Загрузка файла %s на место %s"%(asset["browser_download_url"],ms.MAIN_FILE))
          ms.utils.download_file(asset["browser_download_url"],ms.MAIN_FILE)
          break
    print("Престартер успешно обновлён, перезапуск...")
    if ms.MAIN_FILE.endswith(".py"):
      subprocess.call([sys.executable,ms.MAIN_FILE])
    else:
      subprocess.call([ms.MAIN_FILE])
    sys.exit()
  def install_java(self,*,_try_again=True):
    try:
      return self._install_java()
    except Exception:
      if _try_again:
        return self.install_java(_try_again=False)
      raise
  def _install_java(self):
    data=ms.utils.request("GET",self.ROOT_URL+"java.json").json()
    launcher_java=None
    versions=[LauncherInstaller.JavaVersion(self,i) for i in data["versions"]]
    for version in versions:
      if data["launcher-java"]==version.id:
        launcher_java=version
        version.install()
      else:
        version.install_background()
    return launcher_java.executable
  def install_launcher(self,*,_try_again=True):
    try:
      return self._install_launcher()
    except Exception:
      if _try_again:
        return self.install_launcher(_try_again=False)
      raise
  def _install_launcher(self):
    remote=Format1.from_dict(ms.utils.request("GET",self.ROOT_URL+"Launcher.jar.MS2_hash").json())
    if ms.path.exists(self.dir+"/Launcher.jar"):
      local=Format1.generate(self.dir+"/Launcher.jar",False,hash_type=remote.hash_type)
      if local.file_size==remote.file_size:
        if local.hash_hex==remote.hash_hex:
          print("Лаунчер установлен")
          return self.dir+"/Launcher.jar"
      print("Обновление лаунчера")
    else:
      print("Скачивание лаунчера")
    self.downloader.download2file(self.ROOT_URL+"Launcher.jar",self.dir+"/Launcher.jar")
    print("Проверка целостности лаунчера")
    local=Format1.generate(self.dir+"/Launcher.jar",False,hash_type=remote.hash_type)
    if local.file_size!=remote.file_size:
      raise RuntimeError("Файл повреждён!")
    if local.hash_hex!=remote.hash_hex:
      raise RuntimeError("Файл повреждён!")
    print("Лаунчер установлен")
    return self.dir+"/Launcher.jar"
  def extend_path(self):
    path=os.environ["PATH"].split(os.path.pathsep)
    for dir in ms.dir.list_iter(self.java_dir,type="dir"):
      bin_dir=dir.path+"/bin"
      if ms.path.exists(bin_dir):
        if self.platform.is_windows:
          bin_dir=bin_dir.replace("/","\\")
        if not bin_dir in path:
          path.append(bin_dir)
    os.environ["PATH"]=os.path.pathsep.join(path)
  def run_launcher(self,launcher_args=None,*,debug=False,dev=False,stacktrace=False):
    java=self.install_java()
    jar=self.install_launcher()
    args=[java]+([] if launcher_args is None else launcher_args)
    if debug and not ("-Dlauncher.debug=true" in args):
      args.append("-Dlauncher.debug=true")
      os.environ["DEBUG"]="true"
    if dev and not ("-Dlauncher.dev=true" in args):
      args.append("-Dlauncher.dev=true")
      os.environ["DEV"]="true"
    if stacktrace and not ("-Dlauncher.stacktrace=true" in args):
      args.append("-Dlauncher.stacktrace=true")
      os.environ["STACKTRACE"]="true"
    args+=["-jar",jar]
    self.extend_path()
    print("Запуск лаунчера")
    if "-Dlauncher.dev=true" in args:
      print("Запуск в режиме для разработчиков, запись в журнал недоступна")
      return subprocess.call(args)
    with open(self.dir+"/latest.log","wb") as f:
      return subprocess.call(args,stderr=f,stdout=f)
@ms.utils.main_func(__name__)
def main(args=None,**kw):
  if args is None:
    args=argp.parse_args()
  kw["debug"]=args.debug or os.environ.get("DEBUG")
  kw["dev"]=args.dev or os.environ.get("DEV")
  kw["stacktrace"]=True
  # kw["stacktrace"]=args.stacktrace or os.environ.get("STACKTRACE")
  if kw["dev"]:
    kw["debug"]=True
    # kw["stacktrace"]=True
  inst=LauncherInstaller()
  with ms.utils.OnlyOneInstance(lock_path=inst.dir+"/prestarter.lock"):
    @atexit.register
    def _():
      for i in inst.threads:
        i.join()
    try:
      code=inst.run_launcher(**kw)
    except Exception as exc:
      print("Возникла ошибка при запуске лаунчера:")
      traceback.print_exception(exc)
      print("Попробуйте запустить лаунчер ещё раз")
      print("Если проблема повторяется, обратитесь в чат https://t.me/PawsNBlocks/1")
      return 1
    if code:
      print("Лаунчер завершился с ошибкой")
      print("Попробуйте запустить лаунчер ещё раз")
      print("Если проблема повторяется, обратитесь в чат https://t.me/PawsNBlocks/1 и отправьте лог-файл")
      print("Лог-файл: %s"%inst.dir+"/latest.log")
    return code