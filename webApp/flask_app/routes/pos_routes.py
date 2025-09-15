from flask import Blueprint
from ..controllers import pos_controllers

pos_bp = Blueprint('pos_bp', __name__, template_folder='templates', static_folder='static')

@pos_bp.route('/start', methods=['POST'])
async def start():
    return await pos_controllers.start_new_blockchain()

@pos_bp.route('/create', methods=['POST'])
async def start_bc():
    return await pos_controllers.start_new_blockchain()

@pos_bp.route('/connect', methods=['POST'])
async def connect_to_bc():
    return await pos_controllers.connect_to_blockchain()

@pos_bp.route('/stop', methods=['GET'])
async def stop_peer():
    return await pos_controllers.stop_peer()

@pos_bp.route('/transaction', methods=['POST'])
async def add_tx():
    return await pos_controllers.add_transaction()

@pos_bp.route('/balance', methods=['GET'])
async def find_balance():
    return pos_controllers.account_balance()

@pos_bp.route('/status', methods=['GET'])
def return_status():
    return pos_controllers.get_status()

@pos_bp.route('/chain', methods=['GET'])
def view_chain():
    return pos_controllers.get_chain()

@pos_bp.route('/pending', methods=['GET'])
def view_pending_transactions():
    return pos_controllers.get_pending_transactions()

@pos_bp.route('/peers', methods=['GET'])
def view_known_peers():
    return pos_controllers.get_known_peers()

@pos_bp.route('/check', methods=['GET'])
def server_check():
    return pos_controllers.server_exists_check()

@pos_bp.route('/uploadFile', methods=['POST'])
async def uploadFile():
    return await pos_controllers.uploadFileIPFS()

@pos_bp.route('/downloadFile', methods=['POST'])
def downloadFile():
    return pos_controllers.downloadFileIPFS()