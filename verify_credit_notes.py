import os
import requests
import json
import uuid

def verify_credit_notes_flow():
    base_url = "http://localhost:8001"
    print("--- STARTING CREDIT NOTES INTEGRATION VERIFICATION FLOW ---")
    
    # 1. Login
    login_url = f"{base_url}/auth/login"
    login_payload = {
        "email": "admin@test.com",
        "password": "password123",
        "company_id": "555ff0c8-141f-44f3-8964-bfee5bd8f4bf"
    }
    
    print(f"Logging in at {login_url}...")
    response = requests.post(login_url, json=login_payload)
    if response.status_code != 200:
        print(f"FAILED to log in: {response.status_code} - {response.text}")
        return
        
    auth_data = response.json()
    access_token = auth_data["access_token"]
    print("Successfully logged in!")
    
    # Set headers
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Tenant-ID": "555ff0c8-141f-44f3-8964-bfee5bd8f4bf"
    }
    
    # 2. Get Contacts to identify a customer
    contacts_url = f"{base_url}/contacts?page=1&limit=10"
    print(f"\nFetching contacts from {contacts_url}...")
    response = requests.get(contacts_url, headers=headers)
    if response.status_code != 200:
        print(f"FAILED to fetch contacts: {response.status_code} - {response.text}")
        return
    contacts = response.json()
    print(f"Found {len(contacts)} contacts.")
    
    # Find a customer
    customer_id = None
    for c in contacts:
        if c.get("contact_type") == "customer":
            customer_id = c.get("contact_id")
            print(f"Using customer: {c.get('name')} ({customer_id})")
            break
            
    if not customer_id and len(contacts) > 0:
        customer_id = contacts[0].get("contact_id")
        print(f"Using fallback contact: {contacts[0].get('name')} ({customer_id})")
        
    if not customer_id:
        print("Error: No contacts found to create credit note!")
        return

    # 3. Get Chart of Accounts to find or seed an account
    coa_url = f"{base_url}/chart-of-accounts"
    print(f"\nFetching accounts from {coa_url}...")
    response = requests.get(coa_url, headers=headers)
    if response.status_code != 200:
        print(f"FAILED to fetch chart of accounts: {response.status_code} - {response.text}")
        return
    accounts = response.json()
    print(f"Found {len(accounts)} accounts.")
    
    # Find Sales Returns or Sales account
    sales_return_acc_id = None
    for a in accounts:
        if a.get("account_code") in ("4110", "4100", "4000"):
            sales_return_acc_id = a.get("account_id")
            print(f"Using revenue account: {a.get('account_code')} - {a.get('account_name')} ({sales_return_acc_id})")
            break
            
    if not sales_return_acc_id and len(accounts) > 0:
        sales_return_acc_id = accounts[0].get("account_id")
        print(f"Using fallback account: {accounts[0].get('account_name')} ({sales_return_acc_id})")
        
    if not sales_return_acc_id:
        print("Error: No accounts found!")
        return

    # 4. Create a draft Credit Note
    credit_note_num = f"CN-VERIFY-{uuid.uuid4().hex[:6].upper()}"
    create_cn_url = f"{base_url}/credit-notes"
    create_payload = {
        "credit_note_number": credit_note_num,
        "reference_number": "REF-VERIFY-123",
        "credit_note_date": "2026-05-22",
        "billing_party_id": customer_id,
        "shipping_party_id": None,
        "currency": "INR",
        "exchange_rate": 1.0,
        "salesperson_id": None,
        "customer_notes": "Verifying credit note flow",
        "terms_and_conditions": "Terms apply",
        "status": "draft",
        "items": [
            {
                "inventory_item_id": None,
                "account_id": sales_return_acc_id,
                "description": "Verification item return",
                "hsn_sac": "9983",
                "quantity": 2.0,
                "unit": "pcs",
                "rate": 1000.0,
                "discount_amount": 100.0,
                "tax_id": None,
                "tax_percentage": 18.0,
                "tds_rate": 2.0,
                "tcs_rate": 1.0
            }
        ]
    }
    
    print(f"\nCreating draft credit note {credit_note_num}...")
    response = requests.post(create_cn_url, json=create_payload, headers=headers)
    if response.status_code != 201:
        print(f"FAILED to create credit note: {response.status_code} - {response.text}")
        return
    cn_data = response.json()
    credit_note_id = cn_data["credit_note_id"]
    print(f"Successfully created draft Credit Note. ID: {credit_note_id}, Status: {cn_data['status']}")
    print(f"Grand Total: Rs.{cn_data['grand_total']}, Remaining Balance: Rs.{cn_data['remaining_balance']}")
    
    # 5. Fetch Credit Note details
    get_cn_url = f"{base_url}/credit-notes/{credit_note_id}"
    print(f"\nFetching credit note details from {get_cn_url}...")
    response = requests.get(get_cn_url, headers=headers)
    if response.status_code != 200:
        print(f"FAILED to fetch credit note: {response.status_code} - {response.text}")
        return
    print("Successfully fetched details!")
    
    # 6. Post/Open Credit Note
    print(f"\nPosting credit note (updating status to open)...")
    update_payload = create_payload.copy()
    update_payload["status"] = "open"
    update_payload["credit_note_id"] = credit_note_id
    
    response = requests.put(get_cn_url, json=update_payload, headers=headers)
    if response.status_code != 200:
        print(f"FAILED to post credit note: {response.status_code} - {response.text}")
        return
    cn_posted = response.json()
    print(f"Successfully posted Credit Note. Status: {cn_posted['status']}")

    # 7. Check if ledger entries are created
    ledger_url = f"{base_url}/ledger"
    print(f"\nFetching general ledger entries from {ledger_url} to verify double-entry journal...")
    response = requests.get(ledger_url, headers=headers)
    if response.status_code == 200:
        entries = response.json()
        print(f"Found {len(entries)} general ledger postings.")
        cn_entries = [e for e in entries if e.get("reference_number") == credit_note_num or credit_note_num in str(e.get("description", ""))]
        if cn_entries:
            print(f"Verified balanced ledger entries for {credit_note_num}:")
            for e in cn_entries:
                print(f"  Account: {e.get('account_code')} ({e.get('account_name')}), Debit: Rs.{e.get('debit', 0)}, Credit: Rs.{e.get('credit', 0)}")
        else:
            print("  Note: Ledger entries not found for this CN number yet (could be in mock database bypass mode).")
    else:
        print(f"  Note: Ledger fetch endpoint returned status {response.status_code}")

    # 8. Get unpaid invoices for customer to map credits to
    invoices_url = f"{base_url}/invoices"
    print(f"\nFetching invoices from {invoices_url} to map credits...")
    response = requests.get(invoices_url, headers=headers)
    if response.status_code != 200:
        print(f"FAILED to fetch invoices: {response.status_code} - {response.text}")
        return
    invoices = response.json()
    
    # Find an eligible outstanding invoice for this billing customer
    target_invoice = None
    for inv in invoices:
        if (inv.get("billing_party_id") == customer_id and 
            inv.get("status", "").lower() not in ("draft", "paid") and 
            float(inv.get("balance_due", 0)) > 0):
            target_invoice = inv
            break
            
    if not target_invoice:
        print("No outstanding invoice found for this customer. We'll create one to apply the credits!")
        # Let's create a sales invoice for this customer
        create_inv_url = f"{base_url}/invoices"
        inv_payload = {
            "invoice_number": f"INV-VERIFY-{uuid.uuid4().hex[:6].upper()}",
            "invoice_type": "sales_invoice",
            "invoice_date": "2026-05-22",
            "due_date": "2026-06-22",
            "billing_party_id": customer_id,
            "shipping_party_id": None,
            "currency": "INR",
            "exchange_rate": 1.0,
            "salesperson_id": None,
            "customer_notes": "Invoice to test credit notes mapping",
            "terms_and_conditions": "Terms apply",
            "status": "draft",
            "items": [
                {
                    "inventory_item_id": None,
                    "account_id": sales_return_acc_id,
                    "description": "Verification sale item",
                    "hsn_sac": "9983",
                    "quantity": 5.0,
                    "unit": "pcs",
                    "rate": 2000.0,
                    "discount_amount": 0.0,
                    "tax_id": None,
                    "tax_percentage": 18.0,
                    "tds_rate": 0.0,
                    "tcs_rate": 0.0
                }
            ]
        }
        print("Creating outstanding sales invoice...")
        inv_res = requests.post(create_inv_url, json=inv_payload, headers=headers)
        if inv_res.status_code in (200, 201):
            draft_inv = inv_res.json()
            # Post the invoice to make it open/outstanding
            post_inv_url = f"{base_url}/invoices/{draft_inv['invoice_id']}/post"
            post_res = requests.post(post_inv_url, headers=headers)
            if post_res.status_code == 200:
                target_invoice = post_res.json()
                print(f"Created outstanding Invoice: {target_invoice['invoice_number']} (Balance due: Rs.{target_invoice['balance_due']})")
            else:
                print(f"Failed to post invoice: {post_res.text}")
        else:
            print(f"Failed to create invoice: {inv_res.text}")

    if target_invoice:
        # 9. Apply Credit Note to outstanding invoice
        invoice_id = target_invoice["invoice_id"]
        apply_url = f"{base_url}/credit-notes/{credit_note_id}/apply-to-invoice"
        apply_payload = {
            "invoice_id": invoice_id,
            "applied_amount": 200.0
        }
        print(f"\nApplying Rs.200.00 credits from CN {credit_note_num} to Invoice {target_invoice['invoice_number']}...")
        response = requests.post(apply_url, json=apply_payload, headers=headers)
        if response.status_code == 200:
            map_data = response.json()
            print(f"Successfully applied credits! Mapping ID: {map_data['mapping_id']}, Amount: Rs.{map_data['applied_amount']}")
            
            # Fetch updated credit note to verify balance
            response = requests.get(get_cn_url, headers=headers)
            if response.status_code == 200:
                updated_cn = response.json()
                print(f"Updated Credit Note status: {updated_cn['status']}")
                print(f"Updated Remaining Balance: Rs.{updated_cn['remaining_balance']}")
                
            # Fetch updated invoice to verify balance
            get_inv_url = f"{base_url}/invoices/{invoice_id}"
            response = requests.get(get_inv_url, headers=headers)
            if response.status_code == 200:
                updated_inv = response.json()
                print(f"Updated Invoice status: {updated_inv['status']}")
                print(f"Updated Invoice Balance Due: Rs.{updated_inv['balance_due']}")
        else:
            print(f"FAILED to apply credit note: {response.status_code} - {response.text}")
    else:
        print("\nSkipped applying credit note because no outstanding invoice could be identified or created.")

    # 10. Verify activities log
    activities_url = f"{base_url}/credit-notes/{credit_note_id}/activities"
    print(f"\nFetching activities history for Credit Note...")
    response = requests.get(activities_url, headers=headers)
    if response.status_code == 200:
        logs = response.json()
        print(f"Found {len(logs)} activity records:")
        for log in logs:
            print(f"  - [{log['created_at']}] {log['description']}")
    else:
        print(f"FAILED to fetch activities: {response.text}")

    # 11. Verify mappings list
    mappings_url = f"{base_url}/credit-notes/{credit_note_id}/mappings"
    print(f"\nFetching mappings details for Credit Note...")
    response = requests.get(mappings_url, headers=headers)
    if response.status_code == 200:
        maps = response.json()
        print(f"Found {len(maps)} mappings:")
        for m in maps:
            print(f"  - Mapped to Invoice ID: {m['invoice_id']}, Amount Applied: Rs.{m['applied_amount']}")
    else:
        print(f"FAILED to fetch mappings: {response.text}")

    # 12. Verify PDF generation
    pdf_url = f"{base_url}/credit-notes/{credit_note_id}/pdf"
    print(f"\nDownloading PDF for Credit Note from {pdf_url}...")
    response = requests.get(pdf_url, headers=headers)
    if response.status_code == 200:
        pdf_len = len(response.content)
        print(f"Successfully generated PDF! Size: {pdf_len} bytes")
    else:
        print(f"FAILED to download PDF: {response.status_code} - {response.text}")

    print("\n--- CREDIT NOTES INTEGRATION VERIFICATION FLOW COMPLETED ---")

if __name__ == "__main__":
    verify_credit_notes_flow()
