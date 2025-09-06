import hashlib
import subprocess
from l_java import *
from l_util import *
from MainShortcuts2.sql.sqlite import Database
class FileInfo:
  def __init__(self,inst:"Installer",raw:dict):
    self.name:str=raw["name"]
    self.inst=inst
    self.sha256:str=raw["sha256"]
    self.size:int=raw["size"]
    #
    self.inst.files[self.name]=self
  @property
  def path(self):
    return self.inst.dir+"/"+self.name
  @property
  def url(self):
    return self.inst.URL+self.name
  def check(self,penable=False):
    if not ms.path.exists(self.path):
      return False
    with open(self.path,"rb") as f:
      f.seek(0,os.SEEK_END)
      if f.tell()!=self.size:
        f.close()
        ms.file.delete(self.path)
        return False
      f.seek(0)
      hash=hashlib.sha256()
      pmode=0
      if penable:
        pmode=FakeProgressBar.MODE_DOWNLOAD
        print("Проверка %s"%self.name)
      with FakeProgressBar.create(pmode,max_value=self.size) as pbar:
        for i in f:
          hash.update(i)
          if penable:
            pbar.increment(len(i))
      if hash.hexdigest()!=self.sha256:
        f.close()
        ms.file.delete(self.path)
        return False
    return True
  def download(self,penable=False,retry=True):
    if self.check(penable):
      return True
    if penable:
      print("Скачивание %s"%self.name)
    ms.dir.create(os.path.dirname(self.path))
    self.inst.download_file(self.url,self.path,self.size,penable)
    if not self.check(penable=penable):
      if retry:
        return self.download(penable,False)
      return False
    return True
class Installer(ms.ObjectBase):
  files:dict[str,FileInfo]={}
  URL="https://files.mainplay-tg.ru/PawsNBlocks/launcher/"
  def __init__(self):
    self._arch=None
    self._dir=None
    self._plat=None
    self._runtime_db=None
    self._system=None
    self.java=JavaList(self)
    try:
      for i in ms.utils.request("GET",self.URL+"files.json").json():
        FileInfo(self,i)
    except ConnectionError as exc:
      print("Не удалось получить список файлов. Проверьте соединение с интернетом")
      print(exc)
  @property
  def arch(self) -> str:
    if self._arch is None:
      self._arch=self.plat.arch
      self._arch={"x86_64":"amd64"}.get(self._arch,self._arch)
    return self._arch
  @property
  def dir(self)->str:
    if self._dir is None:
      self._dir=os.path.expanduser("~/%s/MainPlay_TG/PawsNBlocks"%("AppData/Local" if self.plat.is_windows else ".local/share"))
      ms.dir.create(self._dir+"/updates")
    return self._dir
  @property
  def plat(self):
    if self._plat is None:
      self._plat=ms.advanced.get_platform()
    return self._plat
  @property
  def runtime_db(self)->Database:
    if self._runtime_db is None:
      file=self.files["runtime.db"]
      if not file.download():
        raise NotDownloadedException(file.name)
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
  def download_file(self,url:str,path:str,size:int=None,penable=False,retry=True):
    chunk_size=int(1024*1024) # 1 MB
    pmode=0
    if size is None:
      penable=False
    if penable:
      pmode=FakeProgressBar.MODE_DOWNLOAD
    with open(path,"wb") as f:
      try:
        with ms.utils.request("GET",url,stream=True) as resp:
          with FakeProgressBar.create(pmode,max_value=size) as pbar:
            downloaded=0
            for i in resp.iter_content(chunk_size):
              downloaded+=f.write(i)
              if not size is None:
                if downloaded>size:
                  raise ValueError("Broken file")
                if penable:
                  pbar.update(downloaded)
            if not size is None:
              if downloaded!=size:
                raise ValueError("Broken file")
      except Exception:
        f.close()
        ms.file.delete(path)
        if retry:
          return self.download_file(url,path,size,penable,False)
        raise
  def install_launcher(self):
    if "Launcher.jar" in self.files:
      if not self.files["Launcher.jar"].download(True):
        raise NotDownloadedException("Launcher.jar")
    if not ms.path.exists(self.dir+"/Launcher.jar"):
      raise NotDownloadedException("Launcher.jar")
  def start_launcher(self,debug=False,dev=False,stacktrace=True,**kw):
    kw["args"]=[
      self.java.bin,
      "-cp",self.dir+"/Launcher.jar",
      "-Dfile.encoding=UTF-8",
      "-Djdk.attach.allowAttachSelf",
      "-Dlauncher.debug="+str(bool(debug)).lower(),
      "-Dlauncher.dev="+str(bool(dev)).lower(),
      "-Dlauncher.stacktrace="+str(bool(stacktrace)).lower(),
      "-Xmx256M",
      "-XX:+DisableAttachMechanism",
      "pro.gravit.launcher.LauncherEngineWrapper",
    ]
    kw["cwd"]=self.dir
    if dev:
      kw.pop("stderr",None)
      kw.pop("stdout",None)
      print("Запуск в режиме для разработчиков. Запись в файл журнала недоступна")
      return subprocess.call(**kw)
    with open(self.dir+"/latest.log","wb") as f:
      kw["stderr"]=f
      kw["stdout"]=f
      return subprocess.call(**kw)
  def move_old_launcher(self):
    old_dir=os.path.expanduser("~/%s/MainPlay_TG/Paws'n'Blocks"%("AppData/Local" if self.plat.is_windows else ".local/share"))
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
  # XXX
  def run(self,**kw):
    self.move_old_launcher()
    self.install_launcher()
    self.java.install()
    with ms.utils.OnlyOneInstance(lock_path=self.dir+"/launcher.lock"):
      return self.start_launcher(**kw)