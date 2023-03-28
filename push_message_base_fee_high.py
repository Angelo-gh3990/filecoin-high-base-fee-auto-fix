import subprocess
import time

FEE_LIMIT = 1 # change to your setup or to the current Fee Limit you want it to reflect to!
AGE_TIMER = 300

# Store the pending messages and their timestamps in a dictionary
pending_messages = {}


def check_sync_status():
    try:
        # Check if the chain is in sync
        output = subprocess.check_output(["lotus", "info"])
        output_str = output.decode('utf-8')
        if "[sync ok]" not in output_str:
            print("[{}] Warning: Chain out of sync - skipping message checks and replacement".format(time.strftime('%Y-%m-%d %H:%M:%S')))
            return False
        return True
    except Exception as e:
        print("[{}] Error: Failed to check chain sync status: {}".format(time.strftime('%Y-%m-%d %H:%M:%S'), e))
        return False

while True:
    # Check if the chain is in sync
    if not check_sync_status():
        # Wait for 30 seconds before checking again
        print("Sleeping!")
        time.sleep(30)
        print("Sleep Done!")
        continue

    # Run the lotus command to get the pending messages
    process = subprocess.Popen(["lotus", "mpool", "pending", "--local", "--cids"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for the command to finish and get the output
    stdout, stderr = process.communicate()

    if stderr:
        print("[{}] Error: {}".format(time.strftime('%Y-%m-%d %H:%M:%S'), stderr.decode("utf-8")))
    elif not stdout:
        print("[{}] No pending messages found".format(time.strftime('%Y-%m-%d %H:%M:%S')))
    else:
        # Split the output into individual message CIDs
        cids = stdout.decode("utf-8").strip().split("\n")
        print("[{}] Found {} pending messages: {}".format(time.strftime('%Y-%m-%d %H:%M:%S'), len(cids), cids))

        # Check if any new messages have been added to the mpool
        for cid in cids:
            if cid not in pending_messages:
                # Store the timestamp for the new message
                pending_messages[cid] = {"timestamp": time.time()}
                print("[{}] Added message to tracking: {}".format(time.strftime('%Y-%m-%d %H:%M:%S'), cid))

        # Check if any messages have been in the mpool for longer than the age timer
        for cid in list(pending_messages):
            if cid not in cids:
                # Remove the message from tracking if it's no longer pending
                del pending_messages[cid]
                print("[{}] Removed message from tracking: {}".format(time.strftime('%Y-%m-%d %H:%M:%S'), cid))
            else:
                message = pending_messages[cid]
                age = time.time() - message["timestamp"]
                if age > AGE_TIMER:
                    # Replace the old message with a new one
                    process = subprocess.Popen(["lotus", "mpool", "replace", "--auto", "--fee-limit", str(FEE_LIMIT), cid], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()
                    if stderr:
                        print("[{}] Error replacing message {}: {}".format(time.strftime('%Y-%m-%d %H:%M:%S'), cid, stderr.decode("utf-8")))
                    else:
                        # Extract the new CID from the output and strip the prefix
                        new_cid = stdout.decode("utf-8").strip().split(": ")[-1].replace("new message cid: ", "").strip()
                        print("[{}] Replaced message {} with new message: {}".format(time.strftime('%Y-%m-%d %H:%M:%S'), cid, new_cid))

                        # Remove the old message from tracking and add the new one
                        del pending_messages[cid]
                        pending_messages[new_cid] = {"timestamp": time.time()}
                        print("[{}] Added replacement message to tracking: {}".format(time.strftime('%Y-%m-%d %H:%M:%S'), new_cid))

    # Wait for 30 seconds before checking again
    time.sleep(30) 
