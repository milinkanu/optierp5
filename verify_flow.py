import os
import requests
import json

def verify_flow():
    base_url = "http://localhost:8001"
    print("--- STARTING API VERIFICATION FLOW FOR ADMIN ---")
    
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
    
    # 2. Get Quotes
    quotes_url = f"{base_url}/quotes"
    print(f"\nFetching quotes from {quotes_url}...")
    response = requests.get(quotes_url, headers=headers)
    if response.status_code != 200:
        print(f"FAILED to fetch quotes: {response.status_code} - {response.text}")
        return
        
    quotes = response.json()
    print(f"Found {len(quotes)} quotes.")
    
    # Let's see if we have an eligible quote to convert
    convertible_quote = None
    for q in quotes:
        print(f"  Quote ID: {q['quote_id']}, Status: {q['status']}, Number: {q['quote_number']}")
        if q["status"] != "converted":
            convertible_quote = q
            
    if convertible_quote:
        quote_id = convertible_quote["quote_id"]
        convert_quote_url = f"{base_url}/quotes/{quote_id}/convert-invoice"
        print(f"\nConverting quote {quote_id} to invoice...")
        response = requests.post(convert_quote_url, headers=headers)
        print(f"Convert Quote Response status: {response.status_code}")
        if response.status_code in (200, 201):
            print("Successfully converted quote to invoice!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Failed to convert quote: {response.text}")
    else:
        print("\nNo convertible quote found (all quotes are converted or none exist).")
        
    # 3. Get Sales Orders
    so_url = f"{base_url}/sales-orders"
    print(f"\nFetching sales orders from {so_url}...")
    response = requests.get(so_url, headers=headers)
    if response.status_code != 200:
        print(f"FAILED to fetch sales orders: {response.status_code} - {response.text}")
        return
        
    sales_orders = response.json()
    print(f"Found {len(sales_orders)} sales orders.")
    
    convertible_so = None
    for so in sales_orders:
        print(f"  Sales Order ID: {so['sales_order_id']}, Status: {so['status']}, Number: {so['sales_order_number']}")
        if so["status"] not in ("invoiced", "cancelled"):
            convertible_so = so
            
    if convertible_so:
        so_id = convertible_so["sales_order_id"]
        convert_so_url = f"{base_url}/sales-orders/{so_id}/convert-invoice"
        print(f"\nConverting sales order {so_id} to invoice...")
        response = requests.post(convert_so_url, headers=headers)
        print(f"Convert SO Response status: {response.status_code}")
        if response.status_code in (200, 201):
            print("Successfully converted sales order to invoice!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Failed to convert sales order: {response.text}")
    else:
        print("\nNo convertible sales order found (all SOs are invoiced or none exist).")

    # 4. List Invoices
    invoices_url = f"{base_url}/invoices"
    print(f"\nFetching invoices from {invoices_url}...")
    response = requests.get(invoices_url, headers=headers)
    if response.status_code != 200:
        print(f"FAILED to fetch invoices: {response.status_code} - {response.text}")
        return
        
    invoices = response.json()
    print(f"Found {len(invoices)} invoices in database mode.")
    for inv in invoices:
        print(f"  Invoice ID: {inv['invoice_id']}, Number: {inv['invoice_number']}, Grand Total: {inv['invoice_grand_total']}, Status: {inv['status']}")
        
    print("\n--- VERIFICATION FLOW COMPLETED ---")

if __name__ == "__main__":
    verify_flow()
