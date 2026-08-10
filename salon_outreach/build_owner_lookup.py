#!/usr/bin/env python3
"""One-off: compile owner-name research results (public search + Apollo check)
on top of the 90-salon combined list, into a formatted .xlsx.

Not part of the normal 3-stage pipeline -- this is a manual research pass.
"""
import csv

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SRC = "data/combined_90.csv"
OUT = "data/salons_with_owner_research.xlsx"

# handle -> (owner_name, confidence, source_note)
OWNER_DATA = {
    # High confidence -- independently verified against the specific business
    "vesnabeautylounge": ("Vesna Jarawan", "High", "LinkedIn: \"Owner - Vesna Beauty Lounge\"; matches business domain"),
    "rachna_salon": ("Rachna Thakkar", "High", "Multiple sources confirm as founder of Rachna Salon UAE (est. 1980s)"),
    "beautybyfullah.ae": ("Nguyen Phuong Anh (\"Fullah\")", "High", "News profile (IndexBox) on JVC salon opening, matches business"),
    # Medium confidence -- plausible but not fully cross-verified
    "vervebarbershop": ("Celal Girisken", "Medium", "Press credits him as conceiving Verve Barbershop, Dubai Mall"),
    "nikkisbeautysalon": ("Nikki M T", "Medium", "LinkedIn: \"Business Owner - Nikki's beauty salon\" -- plausible match, not address-confirmed"),
    # Self-declared in their own Instagram bio/handle -- not independently
    # verified, but it's literally what the account itself states.
    "arlalouis_hairandmakeupartist": ("Arla Louis", "Self-declared", "From Instagram bio"),
    "refinedbyhaniya": ("Haniya (first name only)", "Self-declared", "From Instagram bio"),
    "shelley_the_global_hairstylist": ("Shelley Douglas", "Self-declared", "From Instagram bio"),
    "theglamlarab": ("Kanwar Sehmi", "Self-declared", "From Instagram bio"),
    "makeup_by_mona___": ("Mona Patel", "Self-declared", "From Instagram bio"),
    "mirrormirror_thehairstudio": ("Natasha Damania", "Self-declared", "From Instagram bio"),
    "barber.mo": ("Mohamad Ebrahim", "Self-declared", "From Instagram bio"),
    "phannky_de_barber": ("Bhraa Phannky", "Self-declared", "From Instagram bio"),
    "ngmhealth_beauty": ("Enriley Childress", "Self-declared", "From Instagram bio"),
    "hairstyles_with_kattia": ("Kattia (first name only)", "Self-declared", "From Instagram handle"),
    "lizziewilliamshair": ("Lizzie Williams", "Self-declared", "From Instagram bio"),
    "hairby_nishat": ("Nishat (first name only)", "Self-declared", "From Instagram handle"),
    "nicoleosullivanhairdxb": ("Nicole O'Sullivan", "Self-declared", "From Instagram handle"),
    "dr.rojmed_clinics_dubai": ("Dr. Rojmed", "Self-declared", "From Instagram bio -- may be a practice name, not a person"),
    "jasminluciahair_1": ("Jasmin (first name only)", "Self-declared", "From Instagram handle; confirmed as a working hairstylist via search, no surname found"),
    "sabbymakeupartist": ("Sabby / Aabby (first name only)", "Self-declared", "From Instagram handle, surname not found"),
    "candace.photographydubai": ("Candace (first name only)", "Self-declared", "From Instagram handle; bio post says \"Founder\", surname not found"),
    "afrocurls_by_ritah": ("Ritah (first name only)", "Self-declared", "From Instagram handle"),
    "fersfantasy": ("\"Fers\" (first name only)", "Self-declared", "From Instagram handle; confirmed Colombian makeup artist via search, full name not found"),
}

FIELDNAMES = [
    "handle", "name", "bio", "website", "business_phone", "business_whatsapp", "business_email",
    "owner_name", "owner_confidence", "owner_source",
]

with open(SRC, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

out_rows = []
for r in rows:
    owner_name, confidence, source = OWNER_DATA.get(r["handle"], ("", "Not found", ""))
    out_rows.append(
        {
            "handle": r["handle"],
            "name": r["name"],
            "bio": r["bio"],
            "website": r["website"],
            "business_phone": r["phone"],
            "business_whatsapp": r["whatsapp"],
            "business_email": r["email"],
            "owner_name": owner_name,
            "owner_confidence": confidence,
            "owner_source": source,
        }
    )

wb = Workbook()
ws = wb.active
ws.title = "Salons"

HEADER_LABELS = {
    "handle": "Instagram Handle",
    "name": "Salon / Display Name",
    "bio": "Bio",
    "website": "Website / Link",
    "business_phone": "Business Phone",
    "business_whatsapp": "Business WhatsApp",
    "business_email": "Business Email",
    "owner_name": "Owner Name (if found)",
    "owner_confidence": "Confidence",
    "owner_source": "Source / Note",
}

header_font = Font(name="Arial", bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
body_font = Font(name="Arial")
wrap = Alignment(vertical="top", wrap_text=True)

not_found_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
high_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
self_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

for col_idx, field in enumerate(FIELDNAMES, start=1):
    cell = ws.cell(row=1, column=col_idx, value=HEADER_LABELS.get(field, field.title()))
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = Alignment(vertical="center")

for row_idx, row in enumerate(out_rows, start=2):
    conf = row["owner_confidence"]
    row_fill = None
    if conf in ("High", "Medium"):
        row_fill = high_fill
    elif conf == "Self-declared":
        row_fill = self_fill
    elif conf == "Not found":
        row_fill = not_found_fill

    for col_idx, field in enumerate(FIELDNAMES, start=1):
        value = row.get(field, "")
        if field == "handle" and value:
            value = f"@{value}"
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.font = body_font
        cell.alignment = wrap
        if row_fill:
            cell.fill = row_fill

widths = {
    "handle": 26, "name": 26, "bio": 45, "website": 26,
    "business_phone": 16, "business_whatsapp": 16, "business_email": 22,
    "owner_name": 26, "owner_confidence": 14, "owner_source": 45,
}
for col_idx, field in enumerate(FIELDNAMES, start=1):
    ws.column_dimensions[get_column_letter(col_idx)].width = widths.get(field, 20)

ws.freeze_panes = "A2"
ws.auto_filter.ref = f"A1:{get_column_letter(len(FIELDNAMES))}{len(out_rows) + 1}"

wb.save(OUT)

found_high_med = sum(1 for r in out_rows if r["owner_confidence"] in ("High", "Medium"))
found_self = sum(1 for r in out_rows if r["owner_confidence"] == "Self-declared")
not_found = sum(1 for r in out_rows if r["owner_confidence"] == "Not found")
print(f"Wrote {len(out_rows)} row(s) to {OUT}")
print(f"  Independently verified owner name: {found_high_med}")
print(f"  Self-declared name in their own bio/handle: {found_self}")
print(f"  No owner name found at all: {not_found}")
