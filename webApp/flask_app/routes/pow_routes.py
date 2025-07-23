from flask import Blueprint
from ..controllers import pow_controllers

chain_bp = Blueprint('chain_bp', __name__, template_folder='templates', static_folder='static')

# @chain_bp.route('/start', methods=['POST'])
# async def start():
#     return await controllers.start_new_blockchain()

@chain_bp.route('/create', methods=['POST'])
async def start_bc():
    return await pow_controllers.start_new_blockchain()

@chain_bp.route('/connect', methods=['POST'])
async def connect_to_bc():
    return await pow_controllers.connect_to_blockchain()

@chain_bp.route('/stop', methods=['GET'])
async def stop_peer():
    return await pow_controllers.stop_peer()

@chain_bp.route('/transaction', methods=['POST'])
async def add_tx():
    return await pow_controllers.add_transaction()


@chain_bp.route('/balance', methods=['GET'])
async def find_balance():
    return pow_controllers.account_balance()

@chain_bp.route('/status', methods=['GET'])
def return_status():
    return pow_controllers.get_status()

@chain_bp.route('/chain', methods=['GET'])
def view_chain():
    return pow_controllers.get_chain()

@chain_bp.route('/pending', methods=['GET'])
def view_pending_transactions():
    return pow_controllers.get_pending_transactions()

@chain_bp.route('/peers', methods=['GET'])
def view_known_peers():
    return pow_controllers.get_known_peers()

@chain_bp.route('/check', methods=['GET'])
def server_check():
    return pow_controllers.server_exists_check()