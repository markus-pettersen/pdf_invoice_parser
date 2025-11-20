import pdfplumber
import re
import os
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
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
    df.to_csv(f"{folder_path}{copy_name}.csv", index=False)


def calculate_cost_despatch(df):
    total_costs = df["total"].sum()
    total_pieces = df["pieces"].sum()
    total_weight = df["weight_kg"].sum()

    cost_per_despatch = round(total_costs / total_pieces, 2)
    fixed_cost = 3.10

    return (cost_per_despatch, total_pieces, total_weight, fixed_cost)


def identify_anomalies(df):

    threshold = 2.99
    anomalies = df[df["cost_per_piece"] > threshold]

    return anomalies


def generate_summary(df, filename):
    actual, total_pieces, total_weight, fixed = calculate_cost_despatch(df)

    anomalous_orders = identify_anomalies(df)

    str_description = "UNDER"

    if fixed < actual:
        str_description = "OVER"

    summary_string = f"""FedEx Retail Despatch
File: {filename}

Actual cost is {str_description} the fixed rate.

Fixed rate:\t\t\t£{fixed:.2f}
Actual cost:\t\t\t£{actual:.2f}
Difference:\t\t\t£{actual - fixed:+.2f} ({100*(actual/fixed - 1):+.2f}%)

Total weight:\t\t\t{total_weight}kg
Total pieces:\t\t\t{total_pieces}
Weight per piece:\t\t\t{total_weight/total_pieces:.2f}kg/piece

{len(anomalous_orders)} anomalous order(s) found.
"""

    if len(anomalous_orders) > 0:
        str_df = anomalous_orders[["shipment", "ship_date", "cost_per_piece"]].to_string(index=False)
        summary_string += f"""\n{str_df}"""

    return summary_string


def log_summary(df, log):
    print("teehee")

