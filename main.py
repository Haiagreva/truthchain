import asyncio
import logging
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from sentence_transformers import SentenceTransformer

from db import supabase
from model import run_ensemble_consensus
from blockchain import log_to_blockchain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TruthChain Oracle API")

logger.info("Loading SentenceTransformer model...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

class ClaimRequest(BaseModel):
    node_id: str
    claim_text: str

class VoteRequest(BaseModel):
    claim_id: str
    node_id: str
    vote: str

@app.get("/")
async def serve_ui():
    return FileResponse("index.html")

@app.get("/nodes")
async def get_nodes():
    res = supabase.table('nodes').select('*').execute()
    return res.data or []

@app.get("/claims")
async def get_claims():
    try:
        claims_res = supabase.table('claims').select('*, nodes(*)').order('created_at', desc=True).execute()
        claims_data = claims_res.data or []
        
        votes_res = supabase.table('votes').select('*').execute()
        votes_data = votes_res.data or []
        
        vote_counts = {}
        for v in votes_data:
            cid = v['claim_id']
            if cid not in vote_counts:
                vote_counts[cid] = {'verify': 0, 'refute': 0, 'node_votes': {}}
            vote_counts[cid][v['vote']] += 1
            vote_counts[cid]['node_votes'][v['node_id']] = v['vote']
            
        for c in claims_data:
            cid = c['id']
            c['vote_counts'] = vote_counts.get(cid, {'verify': 0, 'refute': 0, 'node_votes': {}})
            
        return claims_data
    except Exception as e:
        logger.error(f"Error fetching claims: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/claims")
async def create_claim(req: ClaimRequest):
    try:
        # The Ban Check
        node_res = supabase.table('nodes').select('*').eq('id', req.node_id).execute()
        if not node_res.data:
            raise HTTPException(status_code=400, detail="Invalid node_id")
            
        node = node_res.data[0]
        if node.get('is_banned'):
            banned_until_str = node.get('banned_until')
            if banned_until_str:
                banned_until = datetime.fromisoformat(banned_until_str.replace('Z', '+00:00'))
                if datetime.now(timezone.utc) < banned_until:
                    raise HTTPException(status_code=403, detail="Node is currently banned.")

        # AI Instant-Check
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, embedder.encode, req.claim_text)
        rpc_params = {
            'query_embedding': embedding.tolist(),
            'match_threshold': 0.3,
            'match_count': 3
        }
        match_res = supabase.rpc('match_statements', rpc_params).execute()
        context_texts = [row['content'] for row in (match_res.data or [])]
        context = " ".join(context_texts)
        
        is_flagged = False
        ai_correction_note = None
        
        if context_texts:
            ai_result = await run_ensemble_consensus(req.claim_text, context)
            ai_vote = ai_result.get("final_verdict", "Error")
            
            if ai_vote == "Refuted":
                is_flagged = True
                refuted_count = sum(1 for v in ai_result.get("node_breakdown", []) if v["verdict"] == "Refuted")
                ai_correction_note = f"Ensemble Consensus Reached. {refuted_count}/3 NLP Models refuted this claim based on official sources."
                
                # Issue a Strike
                new_strike_count = (node.get('strike_count') or 0) + 1
                node_handle = node.get('handle', 'unknown')
                
                print(f'\n[AI MODERATOR] Flagged Misinformation: "{req.claim_text[:50]}..." | Strike {new_strike_count}/3 issued to @{node_handle}.')
                
                node_update = {"strike_count": new_strike_count}
                
                # The Hammer
                if new_strike_count >= 3:
                    banned_until_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                    node_update["is_banned"] = True
                    node_update["banned_until"] = banned_until_date
                    print(f'[BAN HAMMER] 3 Strikes reached. @{node_handle} suspended until {banned_until_date}.')
                    
                supabase.table('nodes').update(node_update).eq('id', req.node_id).execute()

        data = {
            "node_id": req.node_id,
            "claim_text": req.claim_text,
            "status": "pending",
            "is_flagged": is_flagged,
            "ai_correction_note": ai_correction_note
        }
        res = supabase.table('claims').insert(data).execute()
        return {"success": True, "claim": res.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vote")
async def cast_vote(req: VoteRequest):
    if req.vote not in ['verify', 'refute']:
        raise HTTPException(status_code=400, detail="Invalid vote type")
        
    try:
        # 1. Fetch the original claim to see who created it
        claim_res = supabase.table('claims').select('node_id').eq('id', req.claim_id).single().execute()
        if not claim_res.data:
            raise HTTPException(status_code=404, detail="Claim not found")

        # 2. Block the author from voting on their own claim
        if claim_res.data['node_id'] == req.node_id:
            raise HTTPException(status_code=400, detail="Authors cannot vote on their own claims.")

        # 3. Proceed with recording the vote
        vote_data = {
            "claim_id": req.claim_id,
            "node_id": req.node_id,
            "vote": req.vote
        }
        try:
            supabase.table('votes').insert(vote_data).execute()
        except Exception as e:
            if 'duplicate key value violates unique constraint' in str(e).lower() or '23505' in str(e):
                raise HTTPException(status_code=400, detail="This node has already voted on this claim.")
            raise e

        # Consensus Check
        votes_res = supabase.table('votes').select('*').eq('claim_id', req.claim_id).execute()
        all_votes = votes_res.data or []
        verify_votes = sum(1 for v in all_votes if v['vote'] == 'verify')
        refute_votes = sum(1 for v in all_votes if v['vote'] == 'refute')
        
        claim_res = supabase.table('claims').select('*').eq('id', req.claim_id).execute()
        if not claim_res.data or claim_res.data[0]['status'] != 'pending':
            return {"success": True, "message": "Vote recorded"}
            
        claim = claim_res.data[0]
        claim_text = claim['claim_text']
        
        # Determine leading human votes
        human_points = max(verify_votes, refute_votes)
        leading_direction = "Verified" if verify_votes >= refute_votes else "Refuted"

        if human_points < 2:
            return {"status": "pending_consensus", "points": human_points, "human_points": human_points}

        # Trigger AI when human points reach at least 2
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, embedder.encode, claim_text)
        rpc_params = {
            'query_embedding': embedding.tolist(),
            'match_threshold': 0.3,
            'match_count': 3
        }
        match_res = supabase.rpc('match_statements', rpc_params).execute()
        context_texts = [row['content'] for row in (match_res.data or [])]
        context = " ".join(context_texts)
        
        if not context_texts:
            ai_vote = "No Evidence"
            ai_confidence = 0.0
            analysis = "No relevant official statements found in database."
        else:
            ai_result = await run_ensemble_consensus(claim_text, context)
            ai_vote = ai_result.get("final_verdict", "Error")
            ai_confidence = ai_result.get("average_confidence", 0.0)
            
            if ai_vote == "Verified":
                verified_count = sum(1 for v in ai_result.get("node_breakdown", []) if v["verdict"] == "Verified")
                analysis = f"Ensemble Consensus Reached. {verified_count}/3 NLP Models verified this claim based on official sources."
            elif ai_vote == "Refuted":
                refuted_count = sum(1 for v in ai_result.get("node_breakdown", []) if v["verdict"] == "Refuted")
                analysis = f"Ensemble Consensus Reached. {refuted_count}/3 NLP Models refuted this claim based on official sources."
            else:
                analysis = "Ensemble Consensus: Uncertain. Models could not reach agreement."

        # Apply Sudden Death Tie-Breaker Logic
        ai_verify_pts = 3 if ai_vote == 'Verified' else 0
        ai_refute_pts = 3 if ai_vote == 'Refuted' else 0

        total_verify = ai_verify_pts + verify_votes
        total_refute = ai_refute_pts + refute_votes
        total_human_votes = verify_votes + refute_votes

        # Check for the 3 vs 3 Deadlock
        is_deadlock = (total_verify == 3 and total_refute == 3)
        
        # Dynamically set max slots (Unlocks 4th only if tied)
        max_human_slots = 4 if is_deadlock else 3

        # Determine Outcome
        if total_verify >= 4:
            status = "Verified"
            analysis_prefix = "VERIFIED: CONSENSUS REACHED"
        elif total_refute >= 4:
            status = "Refuted"
            analysis_prefix = "REFUTED: HUMAN OVERRIDE"
        else:
            status = "pending"
            if is_deadlock:
                analysis_prefix = "SUDDEN DEATH TIE-BREAKER - 3 vs 3"
            else:
                analysis_prefix = f"PENDING CONSENSUS (HUMANS: {total_human_votes}/{max_human_slots})"

        if status != "pending":
            tx_id = await loop.run_in_executor(None, log_to_blockchain, claim_text, status, ai_confidence)
            explorer_url = f"https://testnet.algoexplorer.io/tx/{tx_id}" if "ERROR" not in tx_id else None
            
            update_data = {
                "status": status,
                "blockchain_tx_id": tx_id,
                "blockchain_explorer_url": explorer_url,
                "analysis": f"{analysis_prefix}. {analysis}",
                "confidence_score": ai_confidence
            }
            supabase.table('claims').update(update_data).eq('id', req.claim_id).execute()
            
            return {
                "status": "consensus_reached",
                "points": max(total_verify, total_refute),
                "ai_vote": ai_vote,
                "human_points": human_points,
                "tx_id": tx_id
            }
        else:
            # Update claim analysis but remain pending
            update_data = {
                "analysis": f"{analysis_prefix}. {analysis}",
                "confidence_score": ai_confidence
            }
            supabase.table('claims').update(update_data).eq('id', req.claim_id).execute()
            
            return {
                "status": "pending_consensus",
                "points": max(total_verify, total_refute),
                "ai_vote": ai_vote,
                "human_points": human_points,
                "tx_id": None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error casting vote: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
