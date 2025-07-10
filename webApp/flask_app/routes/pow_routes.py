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

@chain_bp.route('/balance', methods=['GET'])
async def find_balance():
    return pow_controllers.account_balance()

@chain_bp.route('/status', methods=['GET'])
def return_status():
    return pow_controllers.get_status()