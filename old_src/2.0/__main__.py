import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
from argparse import ArgumentParser
from threading import Thread
# IMPORTS.START
import requests
from MainShortcuts2 import ms
from MainShortcuts2.advanced import _Platform
from MainShortcuts2.ms2hash import Format1
from MainShortcuts2.sql.sqlite import Database
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
# IMPORTS.END
NAME="AUTO"
VERSION="AUTO"
argp=ArgumentParser()
argp.add_argument("--debug",action="store_true")
argp.add_argument("--dev",action="store_true")
argp.add_argument("--stacktrace",action="store_true")
class Worker(QThread):
  progress=pyqtSignal()
  finished=pyqtSignal()
  def __init__(self,func,*args,**kwargs):
    QThread.__init__(self)
    self.func=func
    self.args=args
    self.kwargs=kwargs
    self.exc=None
  def run(self):
    try:
      self.func(*self.args,**self.kwargs)
      self.progress.emit()
    except Exception as exc:
      self.exc=exc
      traceback.print_exception(exc)
    finally:
      self.finished.emit()
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
    def install(self,retry=False):
      if ms.path.exists(self.executable):
        return self.inst.mw.log_complete("Java %s установлена"%self.id)
      ms.path.delete(self.dir)
      sel:tuple[str,int,str]=self.inst.runtime_db.select("fileinfo",["filename","filesize","sha1"],{"url":self.url})[0]
      filename,filesize,sha1=sel
      dest_file=ms.path.Path(self.inst.java_dir+"/"+filename)
      self.inst.mw.log_info("Скачивание %s"%filename)
      with ms.path.TempFiles() as temp:
        if not ms.path.exists(dest_file) or True:
          self.inst.mw.download_bar.setMaximum(filesize)
          try:
            self.inst.downloader.download2file(self.url,dest_file,resume=True)
          except Exception as exc:
            self.inst.mw.log_error("Ошибка скачивания: %r"%exc)
            if retry:
              return self.install(False)
            return
          except KeyboardInterrupt:
            raise KeyboardInterrupt("Скачивание прервано")
        self.inst.mw.log_info("Проверка целостности %s"%filename)
        local=Format1.generate(dest_file,True,hash_type="sha1")
        if local.file_size!=filesize:
          raise RuntimeError("Скачанный файл повреждён")
        if local.hash_hex!=sha1:
          raise RuntimeError("Скачанный файл повреждён")
        self.inst.mw.log_info("Распаковка %s"%filename)
        dest_dir=ms.path.Path("%s/.install-%s"%(self.inst.java_dir,self.id))
        temp.add(dest_dir)
        shutil.unpack_archive(dest_file,dest_dir)
        temp.add(dest_file)
        self.inst.mw.log_info("Установка Java %s"%self.id)
        ms.dir.list(dest_dir,type="dir")[0].move(self.dir)
      self.inst.mw.log_info("Java %s успешно установлена"%self.id)
      info=self.db_index
      info.update(self.raw)
      info["developer"]=self.developer
      ms.json.write(self.dir+"/version.json",info)
    def install_background(self):
      if ms.path.exists(self.executable):
        return self.inst.mw.log_complete("Java %s установлена"%self.id)
      self.inst.mw.log_info("Java %s будет установлена в фоне и станет доступна при следующем запуске"%self.id)
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
    self.mw:MainWindow=None
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
      @self._downloader.add_handler(self._downloader.EVENT_STARTED)
      def set_pbar(total_size:None|int,**kw):
        self.mw.download_bar.setValue(0)
        if total_size:
          self.mw.download_bar.setMaximum(total_size)
      @self._downloader.add_handler(self._downloader.EVENT_DOWNLOADING)
      def update_pbar(io,**kw):
        if time.time()-self.mw.download_bar.last_update>1:
          self.mw.download_bar.updateSignal.emit(io.tell())
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
  @property
  def jar(self):
    return self.dir+"/Launcher.jar"
  def update_runtime_db(self):
    self.mw.log_info("Обновление базы данных Java")
    if not self._runtime_db is None:
      self.runtime_db.close()
      self._runtime_db=None
    self.downloader.download2file("https://mainplay-tg.ru/files/runtime.db",self.dir+"/runtime.db")
  def move_old_launcher(self):
    old_dir=os.path.expanduser("~/%s/MainPlay_TG/Paws'n'Blocks"%("AppData/Local" if self.platform.is_windows else ".local/share"))
    if not ms.path.exists(old_dir):
      return
    self.mw.log_info("Удаляю ненужные файлы старого лаунчера...")
    ms.path.delete(old_dir+"/downloading-java")
    ms.path.delete(old_dir+"/launcher-java")
    ms.path.delete(old_dir+"/launcher-jdk")
    ms.path.delete(old_dir+"/launcher-jre")
    ms.path.delete(old_dir+"/Launcher.jar")
    for i in ms.dir.list_iter(old_dir,type="file"):
      dest=self.dir+"/"+i.full_name
      if ms.path.exists(dest):
        self.mw.log_warn("Не удалось переместить файл %s т. к. он уже существует"%i.full_name)
      else:
        self.mw.log_info("Перемещаю файл %s"%i.full_name)
        i.move(dest)
    if ms.path.exists(old_dir+"/updates"):
      for i in ms.dir.list_iter(old_dir+"/updates"):
        dest=self.dir+"/updates/"+i.full_name
        if ms.path.exists(dest):
          self.mw.log_warn("Не удалось переместить модпак %s т. к. он уже существует"%i.full_name)
        else:
          self.mw.log_info("Перемещаю модпак %s"%i.full_name)
          i.move(dest)
      if len(ms.dir.list(old_dir+"/updates"))==0:
        ms.dir.delete(old_dir+"/updates")
    if len(ms.dir.list(old_dir))==0:
      self.mw.log_info("Удаляю пустые папки")
      ms.path.delete(old_dir)
  def self_update(self):
    if os.environ.get("PNB_DISABLE_PRESTARTER_UPDATE"):
      return self.mw.log_warn("Автоматическое обновление престартера отключено")
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
    self.mw.log_info("Обновление престартера (%s -> %s)"%(VERSION,new_version))
    release_info=ms.utils.request("GET","https://api.github.com/repos/%s/%s/releases/latest"%GH_REPO).json()
    assets=release_info["assets"]
    ext=ms.path.Path(ms.MAIN_FILE).ext
    for asset in assets:
      if asset["name"].startswith(NAME):
        if asset["name"].endswith(ext):
          self.mw.log_info("Загрузка файла %s на место %s"%(asset["browser_download_url"],ms.MAIN_FILE))
          self.downloader.download2file(asset["browser_download_url"],ms.MAIN_FILE)
          break
    self.mw.log_info("Престартер успешно обновлён. Изменения вступят в силу после перезапуска")
    time.sleep(5)
  def install_java(self,*,_try_again=True):
    try:
      return self._install_java()
    except Exception as exc:
      self.mw.log_warn("Ошибка: %r. Повторная попытка..."%exc)
      if _try_again:
        return self.install_java(_try_again=False)
      raise
  def _install_java(self):
    self.mw.log_info("Получение списка версий Java")
    data=ms.utils.request("GET",self.ROOT_URL+"java.json").json()
    launcher_java=None
    versions=[LauncherInstaller.JavaVersion(self,i) for i in data["versions"]]
    for version in versions:
      if data["launcher-java"]==version.id:
        launcher_java=version
        version.install()
      else:
        version.install_background()
    self.java=launcher_java.executable
  def install_launcher(self,*,_try_again=True):
    try:
      return self._install_launcher()
    except Exception:
      if _try_again:
        return self.install_launcher(_try_again=False)
      raise
  def _install_launcher(self):
    remote=Format1.from_dict(ms.utils.request("GET",self.ROOT_URL+"Launcher.jar.MS2_hash").json())
    if ms.path.exists(self.jar):
      local=Format1.generate(self.jar,False,hash_type=remote.hash_type)
      if local.file_size==remote.file_size:
        if local.hash_hex==remote.hash_hex:
          return
      self.mw.log_info("Обновление лаунчера")
    else:
      self.mw.log_info("Скачивание лаунчера")
    self.downloader.download2file(self.ROOT_URL+"Launcher.jar",self.dir+"/Launcher.jar")
    self.mw.log_info("Проверка целостности лаунчера")
    local=Format1.generate(self.jar,False,hash_type=remote.hash_type)
    if local.file_size!=remote.file_size:
      raise RuntimeError("Файл повреждён!")
    if local.hash_hex!=remote.hash_hex:
      raise RuntimeError("Файл повреждён!")
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
    args=[self.java]+([] if launcher_args is None else launcher_args)
    if debug and not ("-Dlauncher.debug=true" in args):
      args.append("-Dlauncher.debug=true")
      os.environ["DEBUG"]="true"
    if dev and not ("-Dlauncher.dev=true" in args):
      args.append("-Dlauncher.dev=true")
      os.environ["DEV"]="true"
    if stacktrace and not ("-Dlauncher.stacktrace=true" in args):
      args.append("-Dlauncher.stacktrace=true")
      os.environ["STACKTRACE"]="true"
    args+=["-jar",self.jar]
    self.extend_path()
    if "-Dlauncher.dev=true" in args:
      self.mw.log_warn("Запуск в режиме для разработчиков, запись в журнал недоступна")
      return subprocess.call(args)
    with open(self.dir+"/latest.log","wb") as f:
      return subprocess.call(args,stderr=f,stdout=f)
class MainWindow(QMainWindow):
  class TitleText(QLabel):
    def __init__(self,mw:"MainWindow"):
      QLabel.__init__(self)
      mw.lt.addWidget(self)
      self.setStyleSheet("font-size:16pt;font-weight:bold;")
      self.setText("Установка и запуск лаунчера Paws'n'Blocks")
  class StatusText(QLabel):
    def __init__(self,mw:"MainWindow"):
      QLabel.__init__(self)
      mw.lt.addWidget(self)
      self.setAlignment(Qt.AlignmentFlag.AlignLeft)
      self.setTextFormat(Qt.TextFormat.RichText)
      self.setWordWrap(False)
  class StageBar(QProgressBar):
    def __init__(self,mw:"MainWindow"):
      QProgressBar.__init__(self)
      mw.lt.addWidget(self)
      self.setRange(0,5)
      self.setTextVisible(True)
      self.setValue(0)
  class DownloadBar(StageBar):
    updateSignal=pyqtSignal(int)
    def __init__(self,mw:"MainWindow"):
      self.last_update=0
      MainWindow.StageBar.__init__(self,mw)
      self.updateSignal.connect(self.setValue)
    def setValue(self,value):
      now=time.time()
      if now-self.last_update>1:
        MainWindow.StageBar.setValue(self,value)
        self.last_update=now
  class ActionLog(QTextEdit):
    def __init__(self,mw:"MainWindow"):
      QTextEdit.__init__(self)
      mw.lt.addWidget(self)
      self.mw=mw
      self.setFont(QFont("Consolas"))
      self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
      self.setReadOnly(True)
  def __init__(self,app:QApplication):
    QMainWindow.__init__(self)
    self.app=app
    self.current_status=""
    self.inst:LauncherInstaller=None
    self.stage=0
    # Настройка окна
    self.cw=QWidget()
    self.lt=QVBoxLayout(self.cw)
    self.setCentralWidget(self.cw)
    self.setWindowTitle("Установка PnB-Launcher")
    # Создание виджетов
    self.title=self.TitleText(self)
    self.status=self.StatusText(self)
    self.stage_bar=self.StageBar(self)
    self.download_bar=self.DownloadBar(self)
    self.log=self.ActionLog(self)
    # Открытие окна
    self.show()
  # Ллогирование
  def log_msg(self,text:str,color=None):
    if color:
      text='<font color="%s">%s</font>'%(color,text)
    if text!=self.current_status:
      self.log.insertHtml(text)
      self.log.append("")
      self.status.setText(text)
  def log_error(self,text:str):
    self.log_msg('<b><font color="red"># E</font></b>: '+text)
  def log_complete(self,text:str):
    self.log_msg('<b><font color="green"># C</font></b>: '+text)
  def log_info(self,text:str):
    self.log_msg('<b><font color="blue"># I</font></b>: '+text)
  def log_warn(self,text:str):
    self.log_msg('<b><font color="yellow"># W</font></b>: '+text)
  # Действия
  def start(self):
    self.stage=0
    self._steps = [
      (self.inst.self_update,"Проверка престартера"),
      (self.inst.move_old_launcher,"Перемещение старых файлов"),
      (self.inst.install_java,"Проверка Java"),
      (self.inst.install_launcher,"Проверка лаунчера"),
      (self.inst.run_launcher,"Запуск лаунчера"),
    ]
    self._next_step()
  def _next_step(self):
    if self.stage>=len(self._steps):
      return # self.close()
    func,msg=self._steps[self.stage]
    self.log_info(msg)
    worker=Worker(func)
    @worker.progress.connect
    def _():
      self.log_complete("Завершено")
      self.stage_bar.setValue(self.stage+1)
    @worker.finished.connect
    def _():
      if worker.exc:
        return self.log_error("Ошибка: %r"%worker.exc)
      self.stage+=1
      self._next_step()
    worker.start()
@ms.utils.main_func(__name__)
def main(args=None,**kw):
  app=QApplication(sys.argv)
  inst=LauncherInstaller()
  mw=MainWindow(app)
  inst.mw=mw
  mw.inst=inst
  try:
    with ms.utils.OnlyOneInstance(lock_path=inst.dir+"/prestarter.lock"):
      mw.start()
    return app.exec()
  except Exception as exc:
    print("FATAL ERROR:",file=sys.stderr)
    mw.show()
    traceback.print_exception(exc)