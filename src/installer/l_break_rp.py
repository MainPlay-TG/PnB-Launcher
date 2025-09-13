from zipfile import ZipFile
ALLOWED_FILES=["pack.mcmeta","pack.png"]
CHEAT_FILES=[
  "assets/minecraft/models/block/xray",
  "assets/minecraft/models/block/xray/",
]
def break_resourcepack(path:str):
  saved_files:dict[str,bytes]={}
  with ZipFile(path,"r") as zip:
    exists_files=zip.namelist()
    for file in ALLOWED_FILES:
      if file in exists_files:
        saved_files[file]=zip.read(file)
  with ZipFile(path,"w") as zip:
    for file,data in saved_files.items():
      zip.writestr(file,data)
def check_resourcepack(loc,path):
  if loc!="resourcepacks":
    return False
  try:
    with ZipFile(path,"r") as zip:
      namelist=zip.namelist()
      for i in CHEAT_FILES:
        if i in namelist:
          zip.close()
          break_resourcepack(path)
          return True
      for i in ("assets","assets/"):
        if i in namelist:
          return False
      return True
  except Exception:
    pass
  return False