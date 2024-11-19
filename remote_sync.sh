#!/bin/bash

# Source and destination directories
REMOTE_USER="amcell"
REMOTE_HOST="lachati.com"

LOCAL_DIR="/home/amcell/LLAMA/img-api-llama/DATA/JSON_TO_PROCESS"
REMOTE_DIR="/home/amcell/LLAMA/img-api-llama/DATA/JSON_TO_PROCESS"

# Find the first 5 files in the source directory
FILES=$(ssh "$REMOTE_USER@$REMOTE_HOST" "find $REMOTE_DIR -type f | head -n 15")

# If there are no more files, exit the loop
if [ -z "$FILES" ]; then
	echo "No more files to sync."
	break
fi

# Sync files to the destination
for FILE in $FILES; do
	rsync -avz --remove-source-files "$REMOTE_USER@$REMOTE_HOST:$FILE" "$LOCAL_DIR"
	if [ $? -eq 0 ]; then
		# If sync is successful, remove the source file on the remote server
		echo "REMOVE $FILE"
		ssh "$REMOTE_USER@$REMOTE_HOST" "rm -f $FILE"
	else
		echo "Failed to sync $FILE. Skipping."
	fi
done

echo "Sync completed."

