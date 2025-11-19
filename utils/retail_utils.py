import pdfplumber
import re
import pandas as pd


def extract(input_path):
    rows = []
    dictionary_list = []

    with pdfplumber.open(input_path) as pdf:
        for index, page in enumerate(pdf.pages):
            table_region = (30, 0, 563, 785)

            if index == 0:
                table_region = (30, 297, 563, 785)

            cropped = page.crop(table_region)

            for line in cropped.extract_text().splitlines():
                rows.append(line)

    pattern = re.compile(
        r"""^(?P<shipment>\d{12})\s+                 # Shipment (12 digits)
        (?P<ship_date>\d{2}\/\d{2}\/\d{4})\s+        # Ship Date (dd/mm/yyyy)
        (?P<service>[A-Za-z ]+)\s+                   # Service (Fedex Priority)
        (?P<pieces>\d+)\s+                           # Pieces (int)
        (?P<weight_kg>\d+(?:\.\d+)?\s*kg)\s+         # Weight (d.dd kg)
        (?P<reference>[A-Za-z\-]+)?\s*               # Blank (?)
        (?P<taxable>\d+\.\d{2})\s+                   # Price (dd.dd)
        (?P<non_taxable>\d+\.\d{2})\s+               # Price (d.dd)
        (?P<total>\d+\.\d{2})$                       # taxable + non_taxable (d.dd)
    """,
        re.VERBOSE)

    rows = [row.replace("Cop", "") for row in rows]
    rows = [re.sub(r"(?<=\d)y", "", row) for row in rows]

    for line in rows:
        m = pattern.match(line)
        if m:
            dictionary_list.append(m.groupdict())

    invoice_df = pd.DataFrame.from_records(dictionary_list)

    return invoice_df


def transform(invoice_df):
    df = invoice_df.copy(deep=True)

    # Clean
    df["weight_kg"] = df["weight_kg"].str.replace(" kg", "")

    # Cast as correct types
    df["weight_kg"] = df["weight_kg"].astype("float")
    df["pieces"] = df["pieces"].astype("int")
    df["taxable"] = df["taxable"].astype("float")
    df["non_taxable"] = df["non_taxable"].astype("float")
    df["total"] = df["total"].astype("float")

    df["vat"] = df["taxable"] * 0.2
    df["gross_total"] = df["total"] + df["vat"]
    df["cost_per_piece"] = df["total"] / df["pieces"]

    return df


def load(df, filename):
    copy_name = filename.strip(".pdf")
    folder_path = "outputs/fedex/"
    df.to_csv(f"{folder_path}{copy_name}.csv", index=False)


def calculate_cost_despatch(df):
    total_costs = df["total"].sum()
    total_shipments = df["pieces"].sum()

    cost_per_despatch = round(total_costs / total_shipments, 2)
    fixed_cost = 3.10

    return (cost_per_despatch, total_shipments, fixed_cost)


def identify_anomalies(df):

    threshold = 2.99
    anomalies = df[df["cost_per_piece"] > threshold]

    return anomalies


def generate_summary(df):
    cost_per_despatch, total_shipments, fixed_cost = calculate_cost_despatch(df)

    anomalous_orders = identify_anomalies(df)

    # Date: 5 days plus last entry.

    str_description = "UNDER"

    if fixed_cost < cost_per_despatch:
        str_description = "OVER"

    summary_string = f"""FedEx Retail Despatch

Actual cost is {str_description} the fixed rate.

Fixed rate: £{fixed_cost:.2f}
Actual cost: £{cost_per_despatch:.2f}

{len(anomalous_orders)} anomalous order(s) found.
"""
    return summary_string
