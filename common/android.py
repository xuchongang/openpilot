import os
import binascii
import itertools
import re
import struct
import subprocess
import random

ANDROID = os.path.isfile('/EON')

def getprop(key):
  if not ANDROID:
    return ""
  return subprocess.check_output(["getprop", key], encoding='utf8').strip()

def get_imei(slot):
  slot = str(slot)
  if slot not in ("0", "1"):
    raise ValueError("SIM slot must be 0 or 1")

  ret = parse_service_call_string(service_call(["iphonesubinfo", "3" ,"i32", str(slot)]))
  if not ret:
    # allow non android to be identified differently
    ret = "%015d" % random.randint(0, 1<<32)
  return ret

def get_serial():
  ret = getprop("ro.serialno")
  if ret == "":
    ret = "cccccccc"
  return ret

def get_subscriber_info():
  ret = parse_service_call_string(service_call(["iphonesubinfo", "7"]))
  if ret is None or len(ret) < 8:
    return ""
  return ret

def reboot(reason=None):
  if reason is None:
    reason_args = ["null"]
  else:
    reason_args = ["s16", reason]

  subprocess.check_output([
    "service", "call", "power", "16", # IPowerManager.reboot
    "i32", "0", # no confirmation,
    *reason_args,
    "i32", "1" # wait
  ])

def service_call(call):
  if not ANDROID:
    return None

  ret = subprocess.check_output(["service", "call", *call], encoding='utf8').strip()
  if 'Parcel' not in ret:
    return None

  return parse_service_call_bytes(ret)

def parse_service_call_unpack(r, fmt):
  try:
    return struct.unpack(fmt, r)[0]
  except Exception:
    return None

def parse_service_call_string(r):
  try:
    r = r[8:] # Cut off length field
    r = r.decode('utf_16_be')

    # All pairs of two characters seem to be swapped. Not sure why
    result = ""
    for a, b, in itertools.zip_longest(r[::2], r[1::2], fillvalue='\x00'):
        result += b + a

    result = result.replace('\x00', '')

    return result
  except Exception:
    return None

def parse_service_call_bytes(ret):
  try:
    r = b""
    for hex_part in re.findall(r'[ (]([0-9a-f]{8})', ret):
      r += binascii.unhexlify(hex_part)
    return r
  except Exception:
    return None
