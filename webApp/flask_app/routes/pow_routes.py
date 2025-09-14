from flask import Blueprint
from ..controllers import pow_controllers

pow_bp = Blueprint('pow_bp', __name__, template_folder='templates', static_folder='static')

@pow_bp.route('/start', methods=['POST'])
async def start():
    return await pow_controllers.start_new_blockchain()

@pow_bp.route('/create', methods=['POST'])
async def start_bc():
    return await pow_controllers.start_new_blockchain()

@pow_bp.route('/connect', methods=['POST'])
async def connect_to_bc():
    return await pow_controllers.connect_to_blockchain()

@pow_bp.route('/stop', methods=['GET'])
async def stop_peer():
    return await pow_controllers.stop_peer()

@pow_bp.route('/transaction', methods=['POST'])
async def add_tx():
    return await pow_controllers.add_transaction()

@pow_bp.route('/balance', methods=['GET'])
async def find_balance():
    return pow_controllers.account_balance()

@pow_bp.route('/status', methods=['GET'])
def return_status():
    return pow_controllers.get_status()

@pow_bp.route('/chain', methods=['GET'])
def view_chain():
    return pow_controllers.get_chain()

@pow_bp.route('/pending', methods=['GET'])
def view_pending_transactions():
    return pow_controllers.get_pending_transactions()

@pow_bp.route('/peers', methods=['GET'])
def view_known_peers():
    return pow_controllers.get_known_peers()

@pow_bp.route('/check', methods=['GET'])
def server_check():
    return pow_controllers.server_exists_check()
