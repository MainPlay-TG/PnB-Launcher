import hashlib
import shutil
import subprocess
from l_util import *
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from l_inst import Installer
class JavaVersion(ms.ObjectBase):
  def __init__(self,jlist:"JavaList",raw):
    self._url=None
    self.id:int=raw["id"]
    self.jlist=jlist
    self.raw=raw
    self.tags:list[str]=[ms.json.encode(i) for i in raw["tags"]]
    self.type:str=raw["type"]
    self.version:int=raw["version"]
    jlist.versions[self.id]=self
  @property
  def dir(self)->str:
    return self.jlist.dir+"/"+self.id
  @property
  def bin(self)->str:
    result=self.dir+"/bin/java"
    if self.jlist.inst.plat.is_windows:
      result+=".exe"
    return result
  @property
  def db_index(self):
    return {"arch":self.jlist.inst.arch,"developer":"bellsoft","platform":self.jlist.inst.system,"type":self.type,"version":self.version}
  @property
  def url(self)->str:
    def find(index):
      sel=self.jlist.inst.runtime_db.select("java",["developer","tags","url"],index)
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
        index.pop("developer",None)
        self.developer,self._url=find(index)
      if self._url is None:
        raise ValueError("Не удалось найти подходящую версию Java")
    return self._url
  def install(self):
    if ms.path.exists(self.bin):
      if self.jlist.inst.plat.is_linux:
        subprocess.call(["chmod","+x",self.bin])
      return
    ms.path.delete(self.dir)
    sel:tuple[str,int,str]=self.jlist.inst.runtime_db.select("fileinfo",["filename","filesize","sha1"],{"url":self.url})[0]
    filename,filesize,sha1=sel
    archive=ms.path.Path(self.jlist.dir+"/"+filename)
    if not archive.exists:
      log("Скачивание %s -> %s",self.url,archive.path)
      self.jlist.inst.download_file(self.url,archive,filesize,True)
    log("Проверка %s",archive.full_name)
    with FakeProgressBar.create(FakeProgressBar.MODE_DOWNLOAD,max_value=filesize) as pbar:
      with open(archive,"rb") as f:
        hash=hashlib.sha1()
        for i in f:
          hash.update(i)
          pbar.increment(len(i))
    if hash.hexdigest()!=sha1:
      raise ValueError("Broken file")
    log("Распаковка %s",archive.full_name)
    unpack_dir=ms.path.Path("%s/.install-%s"%(self.jlist.dir,self.id))
    with ms.path.TempFiles(unpack_dir) as temp:
      shutil.unpack_archive(archive,unpack_dir)
      print("Установка %s",self.id)
      ms.dir.list(unpack_dir,type="dir")[0].move(self.dir)
      temp.add(archive)
    if self.jlist.inst.plat.is_linux:
      subprocess.call(["chmod","+x",self.bin])
    info=self.db_index
    info.update(self.raw)
    info["developer"]=self.developer
    ms.json.write(self.dir+"/version.json",info)
class JavaList(ms.ObjectBase):
  DEFAULT_VERSION_ID="jdk-23-full"
  def __init__(self,inst:"Installer"):
    self._bin=None
    self._dir=None
    self.inst=inst
    self.versions:dict[str,JavaVersion]={}
    if "java.json" in inst.files:
      file=inst.files["java.json"]
      file.download()
      data=ms.json.read(file.path)
      self.mv_id:str=data["launcher-java"]
      for i in data["versions"]:
        JavaVersion(self,i)
    else:
      self.mv_id=self.DEFAULT_VERSION_ID
  @property
  def bin(self)->str:
    if self._bin is None:
      self._bin="%s/%s/bin/java"%(self.dir,self.mv_id)
      if self.inst.plat.is_windows:
        self._bin+=".exe"
    return self._bin
  @property
  def dir(self)->str:
    if self._dir is None:
      self._dir="%s/java/%s-%s"%(self.inst.dir,self.inst.system,self.inst.arch)
      ms.dir.create(self._dir)
    return self._dir
  def install(self):
    if self.mv_id in self.versions:
      self.versions[self.mv_id].install()
  def add2path(self):
    path=os.environ["PATH"].split(os.path.pathsep)
    for dir in ms.dir.list_iter(self.dir,type="dir"):
      bin_dir=dir.path+"/bin"
      if ms.path.exists(bin_dir):
        if self.inst.plat.is_windows:
          bin_dir=bin_dir.replace("/","\\")
        if not bin_dir in path:
          path.append(bin_dir)
    os.environ["PATH"]=os.path.pathsep.join(path)
