import json
import shutil
import sys

from PyQt5.QtWidgets import QApplication
from pushbutton import PushButton
import os.path as osp
from utils import newIcon
from widgets import __TXT_SUFFIX__
from widgets import __init__
def process_path(path):
    if getattr(sys, 'frozen', False): #是否Bundle Resource
        base_path = sys._MEIPASS
    else:
        base_path = osp.abspath(".")
    return osp.join(base_path, path)

here = osp.dirname(osp.abspath(__file__))
def get_default_config():

    config_file = process_path("config.json")
    with open(config_file,"r",encoding="utf-8")as f:
        config = json.load(f)

    user_config_file = osp.join(".","conf.json")#"config.json"
    if not osp.exists(user_config_file):
        try:
            shutil.copy(config_file,user_config_file)
        except Exception:
            print("Failed to save confi: {}".format(user_config_file))
    return config
#更新配置文件
def update_dict(target_dict,new_dict):
    for key,value in new_dict.items():
        if key not in target_dict:
            continue
        if isinstance(target_dict[key],dict)and isinstance(value,dict):
            update_dict(target_dict[key],value)
        else:
            target_dict[key]=value


def get_config(config_file = None):
    config = get_default_config()

    if config_file is not None:
        with open(config_file)as f:
            config_from_json = json.load(f)
            if not isinstance(config_from_json, dict):
                with open(config_from_json) as f:
                    print("Loading config file from: {}".format(config_from_json))
            update_dict(config, config_from_json)

    return config
def main():

    #default_config_file = osp.join('.',"conf.json")
    with open("config.json",'r',encoding="utf-8")as f:
        config = json.load(f)
    #global __TXT_SUFFIX__
    #__init__.__TXT_SUFFIX__ = config["fileType"]["__TXT_SUFFIX__"]
    #config = get_config(default_config_file)
    app = QApplication(sys.argv)
    app.setWindowIcon(newIcon("labels"))
    p = PushButton(config = config)
    p.show()
    sys.exit(app.exec_())
if __name__ == "__main__":
    main()


