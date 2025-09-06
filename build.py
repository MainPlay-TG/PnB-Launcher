import os
import platform
import sys
import yaml
from MainShortcuts2 import ms
from pip._internal.cli.main import main as pip_run
from PyInstaller.__main__ import run as pyi_run
NAME="PnB-LauncherInstaller"
VERSION="3.2"
def log(text:str,*values,**kw):
  if len(values)==1:
    text=text%values[0]
  if len(values)>1:
    text=text%values
  kw.setdefault("file",sys.stderr)
  print(text,**kw)
def clear_dir(dir:str):
  ms.dir.create(dir)
  for i in ms.dir.list(dir):
    i.delete()
def edit_source(path:str):
  import_lines=[]
  is_import=False
  new_lines=[]
  old_lines=[i.rstrip() for i in ms.file.read(path).split("\n")]
  for line in old_lines:
    if line.startswith("NAME="):
      line="NAME=%r"%NAME
    if line.startswith("VERSION="):
      line="VERSION=%r"%VERSION
    if line.startswith("# IMPORTS.START"):
      import_lines.clear()
      is_import=True
    if line.startswith("# IMPORTS.END"):
      assert is_import
      new_lines.append("try:")
      for i in import_lines:
        new_lines.append("  %s"%i)
      new_lines.append("except Exception:")
      new_lines.append("  import subprocess")
      new_lines.append("  import sys")
      new_lines.append("  REQIREMENTS_DATA=%r"%ms.file.read("src/requirements.txt"))
      new_lines.append("  REQIREMENTS_PATH=__file__+'.requirements.txt'")
      new_lines.append("  with open(REQIREMENTS_PATH,'w') as f:")
      new_lines.append("    f.write(REQIREMENTS_DATA)")
      new_lines.append("  subprocess.call([sys.executable,'-m','pip','install','-U','-r',REQIREMENTS_PATH])")
      for i in import_lines:
        new_lines.append("  %s"%i)
      import_lines.clear()
      is_import=False
    if not line.lstrip().startswith("#"):
      if is_import:
        import_lines.append(line)
      else:
        new_lines.append(line)
  if is_import:
    raise Exception("Unfinished IMPORTS")
  ms.file.write(path,"\n".join(new_lines))
@ms.utils.main_func(__name__)
def main():
  plat,arch=sys.platform,platform.machine().lower()
  log("Building %s %s to source code and executable file %s %s",NAME,VERSION,plat,arch)
  yml={}
  yml["arch"]=arch
  yml["files"]=[]
  yml["full_name"]="%s_%s"%(NAME,VERSION)
  yml["name"]=NAME
  yml["platform"]=sys.platform
  yml["version"]=VERSION
  ms.path.cwd(ms.MAIN_DIR)
  log("Installing requirements")
  pip_run(["install","-U","-r","src/requirements.txt"])
  for i in ms.dir.list("src",type="dir"):
    src_file=i.path+"/__main__.py"
    if not ms.path.exists(src_file):
      continue
    log("Editing source for %s",i.full_name)
    edit_source(src_file)
    log("Adding source %s to release",i.full_name)
    yml["files"].append({"name":"%s-%s-%s-src.py"%(NAME,VERSION,i.full_name),"path":src_file})
    log("Compiling executable %s for %s %s",i.full_name,plat,arch)
    dist_dir=i.path+"/dist"
    ms.dir.create(dist_dir)
    pyi_run(["--console","--distpath",dist_dir,"--name",NAME+"-"+i.full_name,"--onefile",src_file])
    log("Adding executable %s to release",i.full_name)
    dist_file=ms.dir.list(dist_dir,exts=["exe"])[0].path
    yml["files"].append({"name":"%s-%s-%s-%s.exe"%(NAME,VERSION,i.full_name,arch),"path":dist_file})
  yml["files"].sort(key=lambda i:i["name"])
  ms.file.write("release.yml",yaml.dump(yml))
  log("Complete!")
  ms.json.print(yml)
  if "--release" in sys.argv:
    import requests
    owner=os.environ["GITHUB_OWNER"]
    repo=os.environ["GITHUB_REPO"]
    token=os.environ["GITHUB_TOKEN"]
    kw={"session":requests.Session()}
    kw["json"]={"body":"Автоматический релиз","draft":False,"name":yml["full_name"],"prerelease":False,"tag_name":VERSION}
    kw["session"].headers["Accept"]="application/vnd.github.v3+json"
    kw["session"].headers["Authorization"]="token "+token
    log("Creating release in repo %s/%s",owner,repo)
    with ms.utils.request("POST","https://api.github.com/repos/%s/%s/releases"%(owner,repo),**kw) as resp:
      release:dict=resp.json()
    kw["params"]={}
    kw["session"].headers["Content-Type"]="application/octet-stream"
    for file in yml["files"]:
      log("Uploading file %s",file["name"])
      with open(file["path"],"rb") as f:
        kw["data"]=f
        kw["params"]["name"]=file["name"]
        ms.utils.request("POST",release["upload_url"].replace("{?name,label}",""),**kw)