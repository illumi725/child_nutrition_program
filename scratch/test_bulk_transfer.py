import sys
import os

# Set sys.path so we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

# Set cloud DB mode
os.environ["APP_MODE"] = "cloud"

from core.database import get_db_connection, bulk_transfer_beneficiaries, get_sites

def test_bulk_transfer():
    print("Testing bulk transfer...")
    
    # 1. Fetch some beneficiaries to transfer
    conn = get_db_connection()
    beneficiaries = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT beneficiary_id, site_id, lastname, firstname FROM beneficiaries WHERE deleted_at IS NULL LIMIT 3")
            beneficiaries = cursor.fetchall()
    finally:
        conn.close()
        
    if not beneficiaries:
        print("No active beneficiaries found to test with.")
        return
        
    print(f"Found {len(beneficiaries)} beneficiaries for testing:")
    original_sites = {}
    for b in beneficiaries:
        print(f" - {b['firstname']} {b['lastname']} (ID: {b['beneficiary_id']}, Current Site: {b['site_id']})")
        original_sites[b['beneficiary_id']] = b['site_id']
        
    # 2. Get active sites to choose a target
    sites = get_sites()
    if not sites:
        print("No sites found to transfer to.")
        return
        
    # Pick a site that is different from the current site of the first beneficiary if possible
    first_current = beneficiaries[0]['site_id']
    target_site = None
    for s in sites:
        if s['site_id'] != first_current:
            target_site = s
            break
            
    if not target_site:
        target_site = sites[0]
        
    target_site_id = target_site['site_id']
    print(f"Target site selected for transfer: {target_site['site_name']} (ID: {target_site_id})")
    
    # 3. Perform bulk transfer
    beneficiary_ids = [b['beneficiary_id'] for b in beneficiaries]
    success, err = bulk_transfer_beneficiaries(beneficiary_ids, target_site_id)
    if not success:
        print(f"Bulk transfer failed: {err}")
        return
        
    print("Bulk transfer query executed successfully.")
    
    # 4. Verify in DB
    conn = get_db_connection()
    verified_all = True
    try:
        with conn.cursor() as cursor:
            for bid in beneficiary_ids:
                cursor.execute("SELECT site_id FROM beneficiaries WHERE beneficiary_id = %s", (bid,))
                res = cursor.fetchone()
                if not res or res['site_id'] != target_site_id:
                    print(f"Verification FAILED for beneficiary {bid}: Expected site {target_site_id}, got {res.get('site_id') if res else 'None'}")
                    verified_all = False
                else:
                    print(f"Verification PASSED for beneficiary {bid}")
    finally:
        conn.close()
        
    # 5. Restore original sites
    print("Restoring original sites...")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for bid, orig_sid in original_sites.items():
                cursor.execute("UPDATE beneficiaries SET site_id = %s WHERE beneficiary_id = %s", (orig_sid, bid))
        conn.commit()
        print("Original sites restored successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error restoring original sites: {e}")
    finally:
        conn.close()
        
    if verified_all:
        print("\nALL TESTS PASSED SUCCESSFULLY! ✅")
    else:
        print("\nTESTS FAILED! ❌")

if __name__ == "__main__":
    test_bulk_transfer()
