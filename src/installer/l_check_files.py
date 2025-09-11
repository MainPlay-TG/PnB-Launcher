import requests
from l_util import *
from threading import Thread
from time import time,sleep
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from l_inst import Installer
BLACKLISTED_EXTS=[".txt"]
class CheckFiles(Thread):
  URL="https://mainplay-tg.ru/PnB/api/custom_files/check"
  WAIT_TIME=600
  def __init__(self,inst:"Installer"):
    Thread.__init__(self)
    self.daemon=True
    self.files:dict[str,dict]={}
    self.http=requests.Session()
    self.inst=inst
    self.settings_path=inst.dir+"/settings.json"
  def try_send_report(self):
    if not ms.path.is_file(self.settings_path):
      return False
    settings=ms.json.read(self.settings_path)
    if not "userSettings" in settings:
      return False
    if not "stdruntime" in settings["userSettings"]:
      return False
    if not settings["userSettings"]["stdruntime"].get("oauthAccessToken"):
      return False
    self.http.headers["Authorization"]=settings["userSettings"]["stdruntime"]["oauthAccessToken"]
    try:
      with ms.utils.request("POST",self.URL,json=self.make_report(),session=self.http) as resp:
        data=resp.json()
        for hash in data["rejected"]:
          file=self.files[hash]
          for path in file["files"]:
            ms.file.delete(path)
        return True
    except requests.HTTPError as exc:
      if exc.response.status_code==403:
        if exc.response.reason=="Token expired":
          return False
      raise
  def make_report(self):
    updates_dir=self.inst.dir+"/updates"
    if ms.path.is_dir(updates_dir):
      for version in ms.dir.list_iter(updates_dir,type="dir"):
        for loc in ("resourcepacks","shaderpacks"):
          dir=version.path+"/"+loc
          if ms.path.is_dir(dir):
            for file in ms.dir.list_iter(dir,type="file"):
              if not file.ext in BLACKLISTED_EXTS:
                data={"loc":loc}
                data["name"]=file.full_name
                data["sha256"]=file.hash_hex("sha256")
                data["size"]=file.size
                self.files[data["sha256"]]=data
                self.files[data["sha256"]].setdefault("files",set())
                self.files[data["sha256"]]["files"].add(file.path)
    result=[]
    for orig in self.files.values():
      copy=orig.copy()
      copy.pop("files",None)
      result.append(copy)
    return result
  def run(self):
    try:
      if self.try_send_report():
        return True
    except Exception as exc:
      if os.environ.get("DEBUG"):
        traceback.print_exception(exc)
      return False
    cancel_at=time()+self.WAIT_TIME
    last_mtime=os.path.getmtime(self.settings_path)
    while True:
      if time()>cancel_at:
        return False
      if os.path.getmtime(self.settings_path)!=last_mtime:
        try:
          return self.try_send_report()
        except Exception as exc:
          if os.environ.get("DEBUG"):
            traceback.print_exception(exc)
          return False