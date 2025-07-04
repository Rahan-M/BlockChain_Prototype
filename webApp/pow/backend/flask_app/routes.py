from flask import Blueprint
from . import controllers

chain_bp = Blueprint('chain_bp', __name__, template_folder='templates', static_folder='static')

@chain_bp.route('/start', methods=['POST'])
async def start():
    return await controllers.start_new_blockchain()