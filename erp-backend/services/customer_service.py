from __future__ import annotations
import os
import re
import csv
import io
from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal
from cryptography.fernet import Fernet
from sqlalchemy import select, func, text, update, and_, or_
from sqlalchemy.orm import Session

from models.customers import (
    Customer,
    CustomerAddress,
    CustomerContact,
    CustomerCustomField,
    CustomerDocument,
    CustomerTag,
    CustomerCreateRequest,
    CustomerUpdateRequest
)
from models.db_models import Party
from services.coa_seed import seed_default_chart_of_accounts

# PAN Symmetric Encryption Setup
PAN_ENCRYPTION_KEY = os.getenv("PAN_ENCRYPTION_KEY")
if not PAN_ENCRYPTION_KEY:
    # A persistent, stable symmetric key for development/production fallback
    # Resolves to: "finops_customer_pan_encryption_k" base64 encoded
    PAN_ENCRYPTION_KEY = "Zmlub3BzX2N1c3RvbWVyX3Bhbl9lbmNyeXB0aW9uX2s="

def encrypt_pan(pan: str) -> str | None:
    if not pan:
        return None
    f = Fernet(PAN_ENCRYPTION_KEY.encode())
    return f.encrypt(pan.upper().strip().encode()).decode()

def decrypt_pan(encrypted_pan: str | None) -> str | None:
    if not encrypted_pan:
        return None
    f = Fernet(PAN_ENCRYPTION_KEY.encode())
    try:
        return f.decrypt(encrypted_pan.encode()).decode()
    except Exception:
        return encrypted_pan  # Safeguard fallback to raw string if decryption fails

# GSTIN Checksum and PAN Extraction
def validate_gstin_checksum(gstin: str) -> bool:
    if not gstin:
        return False
    gstin = gstin.upper().strip()
    if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gstin):
        return False

    chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    factor = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1]
    total = 0

    for i in range(14):
        char = gstin[i]
        try:
            value = chars.index(char)
        except ValueError:
            return False
        total += value * factor[i]

    check_digit = (11 - (total % 11)) % 11
    expected_check = chars[check_digit] if check_digit < 10 else str(check_digit - 10)

    return gstin[14] == expected_check

def extract_pan_from_gstin(gstin: str) -> str:
    gstin = gstin.upper().strip()
    return gstin[2:12]

# RLS tenant scope helper
def set_tenant_context(db: Session, company_id: UUID):
    db.execute(text("SET LOCAL app.current_company = :company_id"), {"company_id": str(company_id)})

# Sequence Code Generator
def generate_customer_code(db: Session, company_id: UUID) -> str:
    year = datetime.utcnow().strftime("%Y")
    prefix = f"CUST-{year}-"
    count = db.scalar(
        select(func.count(Customer.customer_id)).where(
            Customer.company_id == company_id,
            Customer.customer_code.like(f"{prefix}%")
        )
    )
    next_seq = (count or 0) + 1
    return f"{prefix}{next_seq:05d}"

# Mock GST Prefill Detail Service
def prefill_gstin_details(gstin: str) -> dict:
    gstin = gstin.upper().strip()
    if not validate_gstin_checksum(gstin):
        raise ValueError("Invalid GSTIN format or checksum")
    
    pan = extract_pan_from_gstin(gstin)
    return {
        "legal_name": "OptiReach Enterprise Solutions Private Limited",
        "trade_name": "OptiReach ERP",
        "gstin": gstin,
        "pan": pan,
        "registration_date": "2020-08-15",
        "gst_status": "Active",
        "gst_registration_type": "regular",
        "billing_address": {
            "attention": "Accounts Department",
            "address_line1": "Suite 805, 8th Floor, Tech Hub Towers",
            "address_line2": "Hitec City, Phase II",
            "city": "Hyderabad",
            "state": "Telangana",
            "zip_code": "500081",
            "country": "India",
            "phone": "+914041234567"
        }
    }

# Create Customer
def create_customer(db: Session, payload: CustomerCreateRequest, company_id: UUID, user_id: UUID) -> Customer:
    set_tenant_context(db, company_id)

    # Validation: GSTIN & PAN Checksum/Match
    if payload.gstin:
        payload.gstin = payload.gstin.upper().strip()
        if not validate_gstin_checksum(payload.gstin):
            raise ValueError("Invalid GSTIN checksum")
        extracted_pan = extract_pan_from_gstin(payload.gstin)
        if payload.pan:
            payload.pan = payload.pan.upper().strip()
            if payload.pan != extracted_pan:
                raise ValueError("PAN does not match the PAN extracted from GSTIN")
        else:
            payload.pan = extracted_pan
    elif payload.pan:
        payload.pan = payload.pan.upper().strip()
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', payload.pan):
            raise ValueError("Invalid PAN format")

    # Duplicate check: Code, Display Name, Email, Mobile, GSTIN
    if payload.customer_code:
        payload.customer_code = payload.customer_code.strip()
        code_exists = db.scalar(select(Customer.customer_id).where(Customer.company_id == company_id, Customer.customer_code == payload.customer_code))
        if code_exists:
            raise ValueError(f"Customer code '{payload.customer_code}' already exists")
    else:
        payload.customer_code = generate_customer_code(db, company_id)

    name_exists = db.scalar(select(Customer.customer_id).where(Customer.company_id == company_id, Customer.display_name == payload.display_name))
    if name_exists:
        raise ValueError(f"Customer display name '{payload.display_name}' already exists")

    if payload.gstin:
        gstin_exists = db.scalar(select(Customer.customer_id).where(Customer.company_id == company_id, Customer.gstin == payload.gstin))
        if gstin_exists:
            raise ValueError(f"Customer with GSTIN '{payload.gstin}' already exists")

    # Prepare billing/shipping address dict for Party table
    billing_dict = None
    shipping_dict = None
    for addr in payload.addresses:
        if addr.address_type == "billing" and not billing_dict:
            billing_dict = addr.model_dump()
        elif addr.address_type == "shipping" and not shipping_dict:
            shipping_dict = addr.model_dump()

    # Step 1: Create matching Party record (100% backward-compatible)
    party_id = uuid4()
    party = Party(
        party_id=party_id,
        company_id=company_id,
        party_name=payload.display_name,
        party_type="customer",
        email=str(payload.email) if payload.email else None,
        phone=payload.phone or payload.mobile,
        gstin=payload.gstin,
        pan=payload.pan,
        payment_terms=payload.payment_terms,
        currency=payload.currency,
        billing_address=billing_dict,
        shipping_address=shipping_dict,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(party)
    db.flush()

    # Step 2: Create Customer record
    customer = Customer(
        customer_id=party_id,
        company_id=company_id,
        customer_code=payload.customer_code,
        customer_name=payload.customer_name,
        customer_type=payload.customer_type,
        display_name=payload.display_name,
        currency=payload.currency,
        email=str(payload.email) if payload.email else None,
        mobile=payload.mobile,
        phone=payload.phone,
        gst_registration_type=payload.gst_registration_type,
        gstin=payload.gstin,
        pan=encrypt_pan(payload.pan),
        payment_terms=payload.payment_terms,
        credit_limit=payload.credit_limit,
        opening_balance=payload.opening_balance,
        opening_balance_type=payload.opening_balance_type,
        msme_status=payload.msme_status,
        msme_registration_no=payload.msme_registration_no,
        cin=payload.cin,
        invoice_delivery_preference=payload.invoice_delivery_preference,
        is_active=True,
        is_deleted=False,
        created_by=user_id,
        updated_by=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(customer)
    db.flush()

    # Step 3: Add child records
    for addr in payload.addresses:
        db_addr = CustomerAddress(
            address_id=uuid4(),
            customer_id=party_id,
            company_id=company_id,
            address_type=addr.address_type,
            attention=addr.attention,
            address_line1=addr.address_line1,
            address_line2=addr.address_line2,
            city=addr.city,
            state=addr.state,
            zip_code=addr.zip_code,
            country=addr.country,
            phone=addr.phone,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(db_addr)

    for ct in payload.contacts:
        db_ct = CustomerContact(
            contact_id=uuid4(),
            customer_id=party_id,
            company_id=company_id,
            first_name=ct.first_name,
            last_name=ct.last_name,
            email=str(ct.email),
            phone=ct.phone,
            mobile=ct.mobile,
            designation=ct.designation,
            is_primary=ct.is_primary,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(db_ct)

    for cf in payload.custom_fields:
        db_cf = CustomerCustomField(
            field_id=uuid4(),
            customer_id=party_id,
            company_id=company_id,
            field_key=cf.field_key,
            field_value=cf.field_value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(db_cf)

    for tag in payload.tags:
        db_tag = CustomerTag(
            tag_id=uuid4(),
            customer_id=party_id,
            company_id=company_id,
            tag_name=tag.strip(),
            created_at=datetime.utcnow()
        )
        db.add(db_tag)

    db.flush()

    # Step 4: Ledger double-entry Journal Posting for Non-Zero Opening Balance
    if payload.opening_balance > 0:
        # Seed default COA if missing
        seed_default_chart_of_accounts(db, company_id)

        ar_row = db.execute(
            text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '1200'"),
            {"company_id": str(company_id)}
        ).fetchone()
        capital_row = db.execute(
            text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '3100'"),
            {"company_id": str(company_id)}
        ).fetchone()

        if ar_row and capital_row:
            ar_account_id = ar_row[0]
            capital_account_id = capital_row[0]
            journal_id = uuid4()
            journal_number = f"OB-{payload.customer_code}"

            # Create in 'draft' status to avoid balance check failures until lines are added
            db.execute(
                text(
                    "INSERT INTO journal_entries (journal_id, company_id, journal_number, journal_type, journal_date, description, reference, status, created_by, updated_by, created_at, updated_at) "
                    "VALUES (:journal_id, :company_id, :journal_number, 'opening', CURRENT_DATE, :description, :reference, 'draft', :created_by, :updated_by, now(), now())"
                ),
                {
                    "journal_id": str(journal_id),
                    "company_id": str(company_id),
                    "journal_number": journal_number,
                    "description": f"Opening Balance for Customer {payload.display_name}",
                    "reference": payload.customer_code,
                    "created_by": str(user_id),
                    "updated_by": str(user_id)
                }
            )

            if payload.opening_balance_type == "debit":
                debit_acc = ar_account_id
                credit_acc = capital_account_id
            else:
                debit_acc = capital_account_id
                credit_acc = ar_account_id

            # Debit Line
            db.execute(
                text(
                    "INSERT INTO journal_entry_lines (journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at) "
                    "VALUES (gen_random_uuid(), :journal_id, :company_id, :account_id, 'debit', :amount, :description, :party_id, now())"
                ),
                {
                    "journal_id": str(journal_id),
                    "company_id": str(company_id),
                    "account_id": str(debit_acc),
                    "amount": float(payload.opening_balance),
                    "description": f"Opening Balance Debit for {payload.display_name}",
                    "party_id": str(party_id)
                }
            )

            # Credit Line
            db.execute(
                text(
                    "INSERT INTO journal_entry_lines (journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at) "
                    "VALUES (gen_random_uuid(), :journal_id, :company_id, :account_id, 'credit', :amount, :description, :party_id, now())"
                ),
                {
                    "journal_id": str(journal_id),
                    "company_id": str(company_id),
                    "account_id": str(credit_acc),
                    "amount": float(payload.opening_balance),
                    "description": f"Opening Balance Credit for {payload.display_name}",
                    "party_id": str(party_id)
                }
            )

            # Post Journal Entry (which triggers RLS and Balance enforcement)
            db.execute(
                text("UPDATE journal_entries SET status = 'posted', updated_at = now() WHERE journal_id = :journal_id"),
                {"journal_id": str(journal_id)}
            )

    db.commit()
    return customer

# List Customers
def list_customers(db: Session, company_id: UUID, page: int = 1, limit: int = 25, q: str | None = None, is_active: bool | None = None) -> list[Customer]:
    set_tenant_context(db, company_id)
    stmt = select(Customer).where(Customer.company_id == company_id, Customer.is_deleted == False)

    if q:
        stmt = stmt.where(
            or_(
                Customer.customer_name.ilike(f"%{q}%"),
                Customer.display_name.ilike(f"%{q}%"),
                Customer.customer_code.ilike(f"%{q}%"),
                Customer.email.ilike(f"%{q}%"),
                Customer.gstin.ilike(f"%{q}%")
            )
        )
    if is_active is not None:
        stmt = stmt.where(Customer.is_active == is_active)

    stmt = stmt.order_by(Customer.customer_name).offset((page - 1) * limit).limit(limit)
    return db.scalars(stmt).all()

# Get Customer by ID
def get_customer(db: Session, customer_id: UUID, company_id: UUID) -> Customer:
    set_tenant_context(db, company_id)
    customer = db.scalar(
        select(Customer).where(Customer.company_id == company_id, Customer.customer_id == customer_id, Customer.is_deleted == False)
    )
    if not customer:
        raise ValueError("Customer not found")
    
    # Decrypt PAN for response serialization
    if customer.pan:
        try:
            customer.pan = decrypt_pan(customer.pan)
        except Exception:
            pass
    return customer

# Update Customer
def update_customer(db: Session, customer_id: UUID, payload: CustomerUpdateRequest, company_id: UUID, user_id: UUID) -> Customer:
    set_tenant_context(db, company_id)
    customer = db.scalar(
        select(Customer).where(Customer.company_id == company_id, Customer.customer_id == customer_id, Customer.is_deleted == False)
    )
    if not customer:
        raise ValueError("Customer not found")

    # Step 1: Update customer fields
    values = payload.model_dump(exclude_unset=True)

    if "gstin" in values and values["gstin"]:
        values["gstin"] = values["gstin"].upper().strip()
        if not validate_gstin_checksum(values["gstin"]):
            raise ValueError("Invalid GSTIN checksum")
        extracted_pan = extract_pan_from_gstin(values["gstin"])
        if "pan" in values and values["pan"]:
            values["pan"] = values["pan"].upper().strip()
            if values["pan"] != extracted_pan:
                raise ValueError("PAN does not match GSTIN")
        else:
            values["pan"] = extracted_pan

    if "pan" in values and values["pan"]:
        values["pan"] = encrypt_pan(values["pan"].upper().strip())

    # Map addresses, contacts, custom fields, tags
    addresses = payload.addresses
    contacts = payload.contacts
    custom_fields = payload.custom_fields
    tags = payload.tags

    values.pop("addresses", None)
    values.pop("contacts", None)
    values.pop("custom_fields", None)
    values.pop("tags", None)

    for k, v in values.items():
        setattr(customer, k, v)
    customer.updated_by = user_id
    customer.updated_at = datetime.utcnow()

    # Step 2: Sync with Party table
    party = db.scalar(select(Party).where(Party.company_id == company_id, Party.party_id == customer_id))
    if party:
        party.party_name = customer.display_name
        party.email = customer.email
        party.phone = customer.phone or customer.mobile
        party.gstin = customer.gstin
        party.pan = decrypt_pan(customer.pan) if customer.pan else None
        party.payment_terms = customer.payment_terms
        party.currency = customer.currency
        party.updated_at = datetime.utcnow()

        # Update JSON addresses on Party as well
        billing_dict = None
        shipping_dict = None
        if addresses is not None:
            for addr in addresses:
                if addr.address_type == "billing" and not billing_dict:
                    billing_dict = addr.model_dump()
                elif addr.address_type == "shipping" and not shipping_dict:
                    shipping_dict = addr.model_dump()
            party.billing_address = billing_dict
            party.shipping_address = shipping_dict

    # Step 3: Handle Child list updates (Overwrite existing ones for simplicity and consistency)
    if addresses is not None:
        db.execute(text("DELETE FROM customer_addresses WHERE customer_id = :cid"), {"cid": str(customer_id)})
        for addr in addresses:
            db_addr = CustomerAddress(
                address_id=uuid4(),
                customer_id=customer_id,
                company_id=company_id,
                address_type=addr.address_type,
                attention=addr.attention,
                address_line1=addr.address_line1,
                address_line2=addr.address_line2,
                city=addr.city,
                state=addr.state,
                zip_code=addr.zip_code,
                country=addr.country,
                phone=addr.phone,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(db_addr)

    if contacts is not None:
        db.execute(text("DELETE FROM customer_contacts WHERE customer_id = :cid"), {"cid": str(customer_id)})
        for ct in contacts:
            db_ct = CustomerContact(
                contact_id=uuid4(),
                customer_id=customer_id,
                company_id=company_id,
                first_name=ct.first_name,
                last_name=ct.last_name,
                email=str(ct.email),
                phone=ct.phone,
                mobile=ct.mobile,
                designation=ct.designation,
                is_primary=ct.is_primary,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(db_ct)

    if custom_fields is not None:
        db.execute(text("DELETE FROM customer_custom_fields WHERE customer_id = :cid"), {"cid": str(customer_id)})
        for cf in custom_fields:
            db_cf = CustomerCustomField(
                field_id=uuid4(),
                customer_id=customer_id,
                company_id=company_id,
                field_key=cf.field_key,
                field_value=cf.field_value,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(db_cf)

    if tags is not None:
        db.execute(text("DELETE FROM customer_tags WHERE customer_id = :cid"), {"cid": str(customer_id)})
        for tag in tags:
            db_tag = CustomerTag(
                tag_id=uuid4(),
                customer_id=customer_id,
                company_id=company_id,
                tag_name=tag.strip(),
                created_at=datetime.utcnow()
            )
            db.add(db_tag)

    db.commit()
    # Recalculate decrypted pan for response
    if customer.pan:
        try:
            customer.pan = decrypt_pan(customer.pan)
        except Exception:
            pass
    return customer

# Soft Delete Customer
def delete_customer(db: Session, customer_id: UUID, company_id: UUID) -> bool:
    set_tenant_context(db, company_id)
    customer = db.scalar(
        select(Customer).where(Customer.company_id == company_id, Customer.customer_id == customer_id, Customer.is_deleted == False)
    )
    if not customer:
        raise ValueError("Customer not found")
    
    customer.is_deleted = True
    customer.updated_at = datetime.utcnow()
    
    # Keep Party table status sync if needed, or simply delete party
    party = db.scalar(select(Party).where(Party.company_id == company_id, Party.party_id == customer_id))
    if party:
        db.delete(party)

    db.commit()
    return True

# CSV Bulk Import Wizard Logic with customizable header mapping & duplicate checks
def bulk_import_customers_csv(db: Session, csv_text: str, column_mapping: dict, company_id: UUID, user_id: UUID) -> dict:
    set_tenant_context(db, company_id)
    reader = csv.DictReader(io.StringIO(csv_text))
    
    imported_count = 0
    duplicate_count = 0
    error_count = 0
    errors = []
    
    # Fetch existing unique identifiers for duplicate checking
    existing_gstins = set(db.scalars(select(Customer.gstin).where(Customer.company_id == company_id, Customer.gstin != None)).all())
    existing_emails = set(db.scalars(select(Customer.email).where(Customer.company_id == company_id, Customer.email != None)).all())
    existing_mobiles = set(db.scalars(select(Customer.mobile).where(Customer.company_id == company_id, Customer.mobile != None)).all())
    
    # Read and map records
    for idx, row in enumerate(reader):
        row_num = idx + 1
        try:
            # Map standard fields using provided column_mapping dict
            def get_mapped(field: str, default=None):
                csv_col = column_mapping.get(field)
                if csv_col and csv_col in row:
                    return row[csv_col].strip()
                return default

            customer_name = get_mapped("customer_name")
            customer_code = get_mapped("customer_code")
            display_name = get_mapped("display_name") or customer_name
            
            if not customer_name:
                raise ValueError("Customer Name is a required field")
            
            email = get_mapped("email")
            mobile = get_mapped("mobile")
            phone = get_mapped("phone")
            gstin = get_mapped("gstin")
            pan = get_mapped("pan")
            currency = get_mapped("currency", "INR")
            customer_type = get_mapped("customer_type", "business").lower()
            gst_registration_type = get_mapped("gst_registration_type", "unregistered").lower()
            payment_terms = get_mapped("payment_terms", "Due on Receipt")
            credit_limit_str = get_mapped("credit_limit", "0")
            opening_balance_str = get_mapped("opening_balance", "0")
            opening_balance_type = get_mapped("opening_balance_type", "debit").lower()
            
            # Clean and parse Numeric
            credit_limit = Decimal(credit_limit_str) if credit_limit_str else Decimal("0")
            opening_balance = Decimal(opening_balance_str) if opening_balance_str else Decimal("0")

            # Validate duplicate rule
            is_dup = False
            dup_reasons = []
            if gstin and gstin.upper().strip() in existing_gstins:
                is_dup = True
                dup_reasons.append(f"GSTIN '{gstin}'")
            if email and email.lower().strip() in existing_emails:
                is_dup = True
                dup_reasons.append(f"Email '{email}'")
            if mobile and mobile.strip() in existing_mobiles:
                is_dup = True
                dup_reasons.append(f"Mobile '{mobile}'")
                
            if is_dup:
                duplicate_count += 1
                errors.append({"row": row_num, "error": f"Duplicate record detected based on: {', '.join(dup_reasons)}"})
                continue
                
            # Build addresses list if present in CSV
            addresses = []
            billing_line1 = get_mapped("billing_address_line1")
            billing_city = get_mapped("billing_city")
            billing_state = get_mapped("billing_state")
            billing_zip = get_mapped("billing_zip")
            if billing_line1 and billing_city and billing_state and billing_zip:
                addresses.append({
                    "address_type": "billing",
                    "attention": get_mapped("billing_attention"),
                    "address_line1": billing_line1,
                    "address_line2": get_mapped("billing_address_line2"),
                    "city": billing_city,
                    "state": billing_state,
                    "zip_code": billing_zip,
                    "country": get_mapped("billing_country", "India"),
                    "phone": get_mapped("billing_phone")
                })
                
            shipping_line1 = get_mapped("shipping_address_line1")
            shipping_city = get_mapped("shipping_city")
            shipping_state = get_mapped("shipping_state")
            shipping_zip = get_mapped("shipping_zip")
            if shipping_line1 and shipping_city and shipping_state and shipping_zip:
                addresses.append({
                    "address_type": "shipping",
                    "attention": get_mapped("shipping_attention"),
                    "address_line1": shipping_line1,
                    "address_line2": get_mapped("shipping_address_line2"),
                    "city": shipping_city,
                    "state": shipping_state,
                    "zip_code": shipping_zip,
                    "country": get_mapped("shipping_country", "India"),
                    "phone": get_mapped("shipping_phone")
                })
                
            # Construct standard Customer Create request
            create_req = CustomerCreateRequest(
                customer_code=customer_code if customer_code else None,
                customer_name=customer_name,
                display_name=display_name,
                customer_type=customer_type,
                currency=currency,
                email=email if email else None,
                mobile=mobile if mobile else None,
                phone=phone if phone else None,
                gst_registration_type=gst_registration_type,
                gstin=gstin if gstin else None,
                pan=pan if pan else None,
                payment_terms=payment_terms,
                credit_limit=credit_limit,
                opening_balance=opening_balance,
                opening_balance_type=opening_balance_type,
                addresses=addresses,
                contacts=[],
                custom_fields=[],
                tags=[]
            )
            
            # Create Customer with a nested transaction savepoint to isolate failures per row
            with db.begin_nested():
                create_customer(db, create_req, company_id, user_id)
            imported_count += 1
            
            # Cache newly created attributes to prevent inter-row duplicates
            if gstin:
                existing_gstins.add(gstin.upper().strip())
            if email:
                existing_emails.add(email.lower().strip())
            if mobile:
                existing_mobiles.add(mobile.strip())
                
        except Exception as e:
            error_count += 1
            errors.append({"row": row_num, "error": str(e)})
            
    return {
        "success": True,
        "imported": imported_count,
        "duplicates": duplicate_count,
        "failed": error_count,
        "errors": errors
    }

