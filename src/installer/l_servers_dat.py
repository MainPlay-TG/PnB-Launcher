import nbtlib
import shutil
from io import BytesIO
from l_util import *
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from l_inst import Installer
def print_changelog(act:str,modpack:str,server:nbtlib.Compound):
  if act=="add":
    return log("%s: Добавлен сервер %s (%s)",modpack,server["name"],server["ip"])
  if act=="delete":
    return log("%s: Удален сервер %s (%s)",modpack,server["name"],server["ip"])
  if act=="replace":
    return log("%s: Заменён IP %s на %s",modpack,server["name"],server["ip"])
  log("%s: %s %s (%s)",modpack,act,server["name"],server["ip"])
class ServerListEditor:
  def __init__(self,inst:"Installer"):
    self.inst=inst
    if "servers.json" in inst.files:
      file=inst.files["servers.json"]
      file.download()
      self.patches:dict=ms.json.read(file.path)
      self.edit_all_modpacks()
    else:
      self.patches={}
  def edit_all_modpacks(self):
    for modpack in self.patches:
      try:
        self.edit_modpack(modpack)
      except Exception as exc:
        log("Ошибка при редактировании списка серверов для модпака %s: %s",modpack,exc)
  def edit_modpack(self,modpack:str):
    ms.dir.create("%s/updates/%s"%(self.inst.dir,modpack))
    path="%s/updates/%s/servers.dat"%(self.inst.dir,modpack)
    if ms.path.exists(path):
      data=nbtlib.load(path)
    else:
      data=nbtlib.File(filename=path)
    data.setdefault("servers",nbtlib.List[nbtlib.Compound]())
    edited=False
    exists=set()
    new_list=nbtlib.List[nbtlib.Compound]()
    patch:dict=self.patches[modpack]
    patch.setdefault("add",{})
    patch.setdefault("delete",[])
    patch.setdefault("replace",{})
    server:nbtlib.Compound
    for server in data["servers"]:
      ip=str(server["ip"]).lower()
      if ip in patch["delete"]:
        edited=True
        print_changelog("delete",modpack,server)
        continue
      if ip in patch["replace"]:
        edited=True
        server["ip"]=nbtlib.String(patch["replace"][ip])
        print_changelog("replace",modpack,server)
      exists.add(ip)
      new_list.append(server)
    for ip,name in patch["add"].items():
      if not ip in exists:
        edited=True
        server=nbtlib.Compound()
        server["acceptTextures"]=nbtlib.Byte(1)
        server["ip"]=nbtlib.String(ip)
        server["name"]=nbtlib.String(name)
        new_list.append(server)
        print_changelog("add",modpack,server)
    if edited:
      with BytesIO() as b:
        data.write(b,byteorder=data.byteorder)
        b.seek(0)
        with open(path,"wb") as f:
          shutil.copyfileobj(b,f)