import hashlib
import os
import subprocess
import sys
import traceback
IS_EXECUTABLE:bool=getattr(sys,"frozen",False)
NAME="NOT_RELEASED"
VERSION="NOT_RELEASED"
# IMPORTS.START
import progressbar
import requests
from MainShortcuts2 import ms
ms.advanced.get_platform
progressbar.FileTransferSpeed
requests.Session
# IMPORTS.END
class FakeProgressBar(progressbar.NullBar):
  MODE_NONE=0
  MODE_COUNT=1
  MODE_DOWNLOAD=2
  def __init__(self):
    self.value=0
  @classmethod
  def create(cls,mode=0,**kw):
    if mode==0:
      return cls()
    if not kw.get("widgets"):
      kw["widgets"]=[progressbar.Percentage()," ",progressbar.GranularBar(left="[",right="]")," "]
      if mode==cls.MODE_COUNT:
        kw["widgets"].append(progressbar.SimpleProgress("%(value_s)s/%(max_value_s)s"))
      if mode==cls.MODE_DOWNLOAD:
        kw["widgets"].append(progressbar.FileTransferSpeed())
      kw["widgets"]+=[" ",progressbar.ETA()]
    kw.setdefault("min_poll_interval",0.5)
    return progressbar.ProgressBar(**kw)
class Prestarter(ms.ObjectBase):
  files:"dict[str,Prestarter.FileInfo]"={}
  URL="https://files.mainplay-tg.ru/PawsNBlocks/launcher/"
  class FileInfo:
    def __init__(self,pres:"Prestarter",raw:dict):
      self.name:str=raw["name"]
      self.pres=pres
      self.sha256:str=raw["sha256"]
      self.size:int=raw["size"]
      #
      self.pres.files[self.name]=self
    @property
    def path(self):
      return self.pres.dir+"/"+self.name
    @property
    def url(self):
      return self.pres.URL+self.name
    def check(self,**kw):
      return self.pres.check_file(self,**kw)
    def download(self,**kw):
      return self.pres.download_file(self.name,**kw)
  def __init__(self):
    self._dir=None
    self._plat=None
    try:
      for i in ms.utils.request("GET",self.URL+"files.json").json():
        self.FileInfo(self,i)
    except ConnectionError as exc:
      print("Не удалось получить список файлов. Проверьте соединение с интернетом")
      print(exc)
  @property
  def dir(self):
    if self._dir is None:
      self._dir=os.path.expanduser("~/%s/MainPlay_TG/PawsNBlocks"%("AppData/Local" if self.plat.is_windows else ".local/share"))
      ms.dir.create(self._dir)
    return self._dir
  @property
  def plat(self):
    if self._plat is None:
      self._plat=ms.advanced.get_platform()
    return self._plat
  def check_file(self,file:"Prestarter.FileInfo",penable=False):
    if not ms.path.exists(file.path):
      return False
    with open(file.path,"rb") as f:
      f.seek(0,os.SEEK_END)
      if f.tell()!=file.size:
        f.close()
        ms.file.delete(file.path)
        return False
      f.seek(0)
      hash=hashlib.sha256()
      pmode=0
      if penable:
        pmode=FakeProgressBar.MODE_DOWNLOAD
        print("Проверка %s"%file.name)
      with FakeProgressBar.create(pmode,max_value=file.size) as pbar:
        for i in f:
          hash.update(i)
          if penable:
            pbar.increment(len(i))
      if hash.hexdigest()!=file.sha256:
        f.close()
        ms.file.delete(file.path)
        return False
    return True
  def download_file(self,name:str,penable=False,retry=True)->bool:
    file=self.files[name]
    if file.check(penable=penable):
      return True
    pmode=0
    chunk_size=int(1024*1024) # 1 MB
    if penable:
      pmode=FakeProgressBar.MODE_DOWNLOAD
      print("Скачивание %s"%name)
    with ms.utils.request("GET",file.url,stream=True) as resp:
      ms.dir.create(os.path.dirname(file.path))
      with open(file.path,"wb") as f:
        with FakeProgressBar.create(pmode,max_value=file.size) as pbar:
          for i in resp.iter_content(chunk_size):
            s=f.write(i)
            if penable:
              pbar.increment(s)
    if not file.check(penable=penable):
      if retry:
        return self.download_file(file.name,penable,False)
      return False
    return True
  # XXX
  def run(self,**kw):
    if IS_EXECUTABLE:
      FILENAME="installer.exe"
      if FILENAME in self.files:
        file=self.files[FILENAME]
        if not file.download(penable=True):
          return False
      FILEPATH=self.dir+"/"+FILENAME
      if not ms.path.exists(FILEPATH):
        return False
      kw["args"]=[FILEPATH]
    else:
      files:list[Prestarter.FileInfo]=[]
      for name in self.files:
        if name.startswith("installer/"):
          files.append(self.files[name])
      if files:
        ok=True
        with FakeProgressBar.create(FakeProgressBar.MODE_COUNT,max_value=len(files)) as pbar:
          for file in files:
            if not file.download(penable=False):
              ok=False
            pbar.increment(1)
        if not ok:
          return False
      FILEPATH=self.dir+"/installer/__main__.py"
      if not ms.path.exists(FILEPATH):
        return False
      new_pythonpath=[self.dir+"/installer"]
      old_pythonpath=os.environ.get("PYTHONPATH","").split(os.path.pathsep)
      for i in old_pythonpath:
        if i:
          i=i.replace("\\","/").rstrip("/")
          if i:
            if not i in new_pythonpath:
              new_pythonpath.append(i)
      if self.plat.is_windows:
        new_pythonpath=[i.replace("/","\\") for i in new_pythonpath]
      kw["args"]=[sys.executable,FILEPATH]
      os.environ["PYTHONPATH"]=os.path.pathsep.join(new_pythonpath)
    if len(sys.argv)>1:
      kw["args"]+=sys.argv[1:]
    subprocess.call(**kw)
    return True
@ms.utils.main_func(__name__)
def main():
  pres=Prestarter()
  try:
    result=pres.run()
  except Exception as exc:
    if isinstance(exc,ConnectionError):
      print("Не удалось связаться с сервером. Проверьте интернет-соединение")
    else:
      print("Неизвестная ошибка")
      traceback.print_exception(exc)
    print("Нажмите Enter чтобы закрыть")
    input()
    return 1
  if not result:
    print("Не удалось скачать файлы. Попробуйте позже")
    print("Нажмите Enter чтобы закрыть")
    input()
    return 1