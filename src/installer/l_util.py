import os
import progressbar
import sys
import traceback
from MainShortcuts2 import ms
IS_EXECUTABLE:bool=getattr(sys,"frozen",False)
log=ms.utils.mini_log
class NotDownloadedException(Exception):
  def __init__(self,*files:str):
    Exception.__init__(self,*files)
    self.files=set(files)
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