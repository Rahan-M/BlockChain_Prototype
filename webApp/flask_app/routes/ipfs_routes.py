from flask import Blueprint
from ..controllers import ipfs_controllers

ipfs_bp = Blueprint('ipfs_bp', __name__, template_folder='templates', static_folder='static')

@ipfs_bp.route('/uploadFile', methods=['POST'])
async def uploadFile():
    return await ipfs_controllers.uploadFileIPFS()

@ipfs_bp.route('/downloadFile', methods=['POST'])
def downloadFile():
    return ipfs_controllers.downloadFileIPFS()