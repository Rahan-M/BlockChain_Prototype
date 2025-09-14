from flask import request, jsonify
from blockchain.pow.ipfs import download_ipfs_file_subprocess
import os

async def uploadFileIPFS():
    global peer_instance
    if(not request.is_json):
        return jsonify({"success":False, "error": "Request must be JSON"})

    data=request.get_json()
    desc=data.get('desc')
    path=data.get('path')
    await peer_instance.uploadFile(desc, path)

    #The output of the first method, os.path.join(), would be home/desktop/newFolder/my_story.txt on a Linux or macOS system. On a Windows system, it would automatically be home\desktop\newFolder\my_story.txt, correctly handling the different slash.
    return jsonify({"success":True, "message": "File Uploaded"})

def downloadFileIPFS():
    global peer_instance
    if(not request.is_json):
        return jsonify({"success":False, "error": "Request must be JSON"})

    data=request.get_json()
    cid=data.get('cid')
    path=data.get('path')
    name=data.get('name')
    full_path=os.path.join(path, name)
    print(full_path)
    download_ipfs_file_subprocess(cid, full_path)
    return jsonify({"success":True, "message": "File Downloaded"})
