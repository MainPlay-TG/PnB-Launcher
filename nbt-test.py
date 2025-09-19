import nbtlib
from MainShortcuts2 import ms
file="C:/Users/MurchaevRoma/AppData/Local/MainPlay_TG/PawsNBlocks/updates/PnB-Vanilla/servers.dat"
data=nbtlib.load(file)
ms.json.print(data,mode="c")
create={"test.ru":"Just test"}
delete={"node2.mistserver.online:22865"}
exist=set()
new_list=nbtlib.List[nbtlib.Compound]()
print(repr(data["servers"]))
for server in data["servers"]:
  print(repr(server))
  if server["ip"] in delete:
    continue
  new_list.append(server)
  exist.add(server["ip"])
for ip,name in create.items():
  if ip not in exist:
    server=nbtlib.Compound()
    server["ip"]=nbtlib.String(ip)
    server["name"]=nbtlib.String(name)
    server["acceptTextures"]=nbtlib.Byte(1)
    new_list.append(server)
data["servers"]=new_list
data.save()
ms.json.print(data,mode="c")