#!/usr/bin/env bash

OUTPUT_DIR=/mnt/precious/Photos/by_year
SCRIPT_DIR="/mnt/precious/Photos/photo-organiser"

source "${SCRIPT_DIR}/venv/bin/activate"

# Pixel backups
"${SCRIPT_DIR}/organize.py" \
  --output-directory "${OUTPUT_DIR}" \
  --linked-files \
  /mnt/precious/Photos/Pixel*

## Older stuff
#./organize.py \
#  --output-directory "${OUTPUT_DIR}" \
#  --use-exif \
#  --linked-files \
#  /net/precious/Photos/Phone \
#  /net/precious/Photos/Phone\ Backup/Camera \
#  /net/precious/Photos/Phone\ Backup/Pictures \
#  /net/precious/Photos/Phone\ Backup/Sent\ Snaps
#
## Older stuff with diff filenames
#./organize.py \
#  --filename-pattern ".*\.([Jj][Pp][Ee]?[Gg]|[Mm][Pp]4|[Dd][Nn][Gg]|[Aa][Rr][Ww])$" \
#  --output-directory "${OUTPUT_DIR}" \
#  --use-exif \
#  --linked-files \
#  /net/precious/Photos/Camera/Misc \
#  /net/precious/Photos/Camera/100MSDCF \
#  /net/precious/Photos/Misc \
#  /net/precious/Photos/Xiaomi_Backup

# pregenerate thumbnails
# ./thumbnail.py ${OUTPUT_DIR}
