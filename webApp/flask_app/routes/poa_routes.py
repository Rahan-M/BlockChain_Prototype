from flask import Blueprint
from ..controllers import poa_controllers

poa_bp = Blueprint('poa_bp', __name__, template_folder='templates', static_folder='static')

@poa_bp.route('/start', methods=['POST'])
async def start():
    return await poa_controllers.start_new_blockchain()

@poa_bp.route('/create', methods=['POST'])
async def start_bc():
    return await poa_controllers.start_new_blockchain()

@poa_bp.route('/connect', methods=['POST'])
async def connect_to_bc():
    return await poa_controllers.connect_to_blockchain()

@poa_bp.route('/stop', methods=['GET'])
async def stop_peer():
    return await poa_controllers.stop_peer()

@poa_bp.route('/transaction', methods=['POST'])
async def add_tx():
    return await poa_controllers.add_transaction()

@poa_bp.route('/balance', methods=['GET'])
async def find_balance():
    return poa_controllers.account_balance()

@poa_bp.route('/status', methods=['GET'])
def return_status():
    return poa_controllers.get_status()

@poa_bp.route('/chain', methods=['GET'])
def view_chain():
    return poa_controllers.get_chain()

@poa_bp.route('/pending', methods=['GET'])
def view_pending_transactions():
    return poa_controllers.get_pending_transactions()

@poa_bp.route('/peers', methods=['GET'])
def view_known_peers():
    return poa_controllers.get_known_peers()

@poa_bp.route('/miners', methods=['GET'])
def view_miners():
    return poa_controllers.get_current_miners()

@poa_bp.route('/add', methods=['POST'])
async def add_miner():
    return await poa_controllers.add_miner()

@poa_bp.route('/remove', methods=['POST'])
async def remove_miner():
    return await poa_controllers.remove_miner()

@poa_bp.route('/check', methods=['GET'])
def server_check():
    return poa_controllers.server_exists_check()

@poa_bp.route('/uploadFile', methods=['POST'])
async def uploadFile():
    return await poa_controllers.uploadFileIPFS()

@poa_bp.route('/downloadFile', methods=['POST'])
def downloadFile():
    return poa_controllers.downloadFileIPFS()