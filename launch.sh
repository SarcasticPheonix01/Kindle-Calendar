#!/bin/sh
export LD_LIBRARY_PATH=/mnt/us/python3/lib:$LD_LIBRARY_PATH
/mnt/us/python3/bin/python3.11 /mnt/us/extensions/Calendar_App/app.py
echo
echo "[Process Finished - Press Enter to Close]"
read dummy
