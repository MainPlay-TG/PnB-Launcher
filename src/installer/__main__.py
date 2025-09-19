NAME="NOT_RELEASED"
VERSION="NOT_RELEASED"
# IMPORTS.START
import nbtlib
import progressbar
import requests
from MainShortcuts2 import ms
ms.advanced.get_platform
progressbar.FileTransferSpeed
requests.Session
# IMPORTS.END
from l_inst import *
@ms.utils.main_func(__name__)
def main():
  print(NAME,VERSION)
  inst=Installer()
  try:
    result=inst.run()
  except Exception as exc:
    if isinstance(exc,ConnectionError):
      print("Не удалось связаться с сервером. Проверьте интернет-соединение")
    elif isinstance(exc,NotDownloadedException):
      print("Не удалось скачать файл(ы):")
      for i in exc.files:
        print("- "+i)
    else:
      print("Неизвестная ошибка")
      traceback.print_exception(exc)
    print("Нажмите Enter чтобы закрыть")
    input()
    return 1
  return result