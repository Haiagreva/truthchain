import os
import json
import logging
from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk.transaction import PaymentTxn
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

ALGO_MNEMONIC = os.getenv("ALGO_MNEMONIC")

# Use public TestNet node
ALGOD_ADDRESS = "https://testnet-api.algonode.cloud"
ALGOD_TOKEN = ""

algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)

def log_to_blockchain(claim: str, verdict: str, confidence: float) -> str:
    try:
        if not ALGO_MNEMONIC:
            raise ValueError("ALGO_MNEMONIC is missing")
            
        private_key = mnemonic.to_private_key(ALGO_MNEMONIC.strip('"'))
        sender_address = account.address_from_private_key(private_key)
        
        params = algod_client.suggested_params()
        
        note_data = {
            "claim": claim,
            "verdict": verdict,
            "confidence": confidence
        }
        note = json.dumps(note_data).encode()
        
        # 0-ALGO transaction to self
        unsigned_txn = PaymentTxn(
            sender=sender_address,
            sp=params,
            receiver=sender_address,
            amt=0,
            note=note
        )
        
        signed_txn = unsigned_txn.sign(private_key)
        tx_id = algod_client.send_transaction(signed_txn)
        
        return tx_id
    except Exception as e:
        logger.error(f"Blockchain logging failed: {e}")
        return f"ERROR: {str(e)}"
