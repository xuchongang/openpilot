import os
import json

from datetime import datetime, timedelta
from selfdrive.swaglog import cloudlog
from selfdrive.version import version, terms_version, training_version, get_git_commit, get_git_branch, get_git_remote
from common.android import get_imei, get_serial, get_subscriber_info
from common.api import api_get
from common.params import Params
from common.file_helpers import mkdirs_exists_ok

def register():
  params = Params()
  params.put("Version", version)
  params.put("TermsVersion", terms_version)
  params.put("TrainingVersion", training_version)
  params.put("GitCommit", get_git_commit())
  params.put("GitBranch", get_git_branch())
  params.put("GitRemote", get_git_remote())
  params.put("SubscriberInfo", get_subscriber_info())

  # create a key for auth
  # your private key is kept on your device persist partition and never sent to our servers
  # do not erase your persist partition
  if not os.path.isfile("/persist/comma/id_rsa.pub"):
    cloudlog.warning("generating your personal RSA key")
    mkdirs_exists_ok("/persist/comma")
    assert os.system("openssl genrsa -out /persist/comma/id_rsa.tmp 2048") == 0
    assert os.system("openssl rsa -in /persist/comma/id_rsa.tmp -pubout -out /persist/comma/id_rsa.tmp.pub") == 0
    os.rename("/persist/comma/id_rsa.tmp", "/persist/comma/id_rsa")
    os.rename("/persist/comma/id_rsa.tmp.pub", "/persist/comma/id_rsa.pub")

  # make key readable by app users (ai.comma.plus.offroad)
  os.chmod('/persist/comma/', 0o755)
  os.chmod('/persist/comma/id_rsa', 0o744)

  dongle_id, access_token = params.get("DongleId", encoding='utf8'), params.get("AccessToken", encoding='utf8')
  public_key = open("/persist/comma/id_rsa.pub").read()

  # create registration token
  # in the future, this key will make JWTs directly
  private_key = open("/persist/comma/id_rsa").read()

  # late import
  import jwt
  register_token = jwt.encode({'register':True, 'exp': datetime.utcnow() + timedelta(hours=1)}, private_key, algorithm='RS256')

  try:
    cloudlog.info("getting pilotauth")
    resp = api_get("v2/pilotauth/", method='POST', timeout=15,
                   imei=get_imei(0), imei2=get_imei(1), serial=get_serial(), public_key=public_key, register_token=register_token)
    dongleauth = json.loads(resp.text)
    dongle_id, access_token = dongleauth["dongle_id"], dongleauth["access_token"]

    params.put("DongleId", dongle_id)
    params.put("AccessToken", access_token)
    return dongle_id, access_token
  except Exception:
    cloudlog.exception("failed to authenticate")
    if dongle_id is not None and access_token is not None:
      return dongle_id, access_token
    else:
      return None

if __name__ == "__main__":
  print(register())
