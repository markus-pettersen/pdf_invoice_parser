import pdfplumber
import re
import pandas as pd
import csv
import os


# ETL process
def extract(input_path):
    rows = []
    dictionary_list = []

    with pdfplumber.open(input_path) as pdf:
        for page in pdf.pages:

            table_region = (55, 306, 564, 489)       # x0, top, x1, bottom
            cropped = page.crop(table_region)

            for line in cropped.extract_text().splitlines():
                rows.append(line)

    pattern = re.compile(
        r"""^(?P<description>.*?)\s+                # description (text)
        (?P<quantity>\d{1,3}(?:,\d{3})*)\s+         # quantity (1,234 or 12)
        (?P<unit_price>\d+\.\d{2})\s+               # unit price (2.09)
        (?P<tax_code>[A-Z]?)\s*                     # VAT code (S, O, X...)
        (?P<net_cost>\d{1,3}(?:,\d{3})*\.\d{2})$    # total net cost (2,679.83)
    """,
        re.VERBOSE)

    for line in rows:
        m = pattern.match(line)
        if m:
            dictionary_list.append(m.groupdict())
        else:
            if dictionary_list:
                previous_entry = dictionary_list[-1]
                previous_entry["description"] += " " + line
            else:
                return pd.DataFrame()

    invoice_df = pd.DataFrame.from_records(dictionary_list)

    return invoice_df


def transform(invoice_df):
    df = invoice_df.copy(deep=True)

    # Clean numerical columns
    df["net_cost"] = df["net_cost"].str.replace(",", "")
    df["quantity"] = df["quantity"].str.replace(",", "")

    # Cast as proper data types
    df["net_cost"] = df["net_cost"].astype("float")
    df["unit_price"] = df["unit_price"].astype("float")
    df["quantity"] = df["quantity"].astype("int")
    df["tax_code"] = df["tax_code"].astype("category")

    # Shorten description column
    df["description"] = df["description"].str.replace(r"\s\(.*", "", regex=True)

    # Calculate new columns
    df["vat"] = df.apply(lambda row: calculate_tax(row["tax_code"], row["net_cost"]), axis=1)
    df["total_cost"] = df["vat"] + df["net_cost"]
    df["category"] = df.apply(lambda row: classify_charge(row["description"]), axis=1)
    df["size"] = df.apply(lambda row: order_size(row["description"], row["category"]), axis=1)

    week_number = df["description"].iloc[0]
    week_matches = re.findall(r"WK(\d{1,2})", week_number)
    df["week"] = week_matches[0]
    df["week"] = df["week"].astype("int")

    # drop rows with zero charges (metadata rows)
    df_zero = df[df["net_cost"] == 0]
    df = df.drop(df_zero.index, axis=0)

    return df


def load(df):
    folder_path = "outputs/evri/"
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
    file_name = "evri_week_" + str(df["week"].iloc[0])
    df.to_csv(f"outputs/evri/{file_name}.csv", index=False)


# Reporting functions
def calculate_costs(df):
    week_no = df["week"].iloc[0]
    despatch_df = df[df["category"] == "Despatch"]
    # Use pre-VAT cost
    total_costs = despatch_df["net_cost"].sum()
    total_orders = despatch_df["quantity"].sum()
    cost_per_despatch = round(total_costs / total_orders, 2)
    fixed_cost = 2.44  # Hard coded fixed cost
    return (int(week_no), float(cost_per_despatch), fixed_cost, int(total_orders))


def generate_summary(df):
    week, actual, fixed, total_orders = calculate_costs(df)
    str_description = "UNDER"

    if actual > fixed:
        str_description = "OVER"

    summary_string = f"""Evri E-commerce Despatch
Week: {str(week)}

The actual cost is {str_description} the fixed rate.

Fixed rate:\t\t\t£{fixed} per despatch
Actual cost:\t\t\t£{actual} per despatch
Difference:\t\t\t£{actual - fixed:+.2f} ({100*(actual/fixed - 1):+.2f}%)
Total despatches:\t\t\t{total_orders:,}
"""
    return summary_string

def log_summary(df, log):
    week, actual, fixed, total_orders = calculate_costs(df)
    difference = round(actual - fixed, 2)

    summary_row = [
        str(week),
        str(actual),
        str(fixed),
        str(difference),
        str(total_orders)
        ]

    # check if row already exists
    existing_rows = set()

    with open(log, mode="r", newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            existing_rows.add(tuple(row))

    if tuple(summary_row) in existing_rows:
        return True
    else:
        with open(log, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(summary_row)
        return False


# Transforming helper functions
def calculate_tax(code, cost):
    vat_codes = {"S": 0.2, "O": 0, "X": 0, "W": 0, "Z": 0}
    tax_rate = vat_codes.get(code)
    payable_tax = tax_rate * cost
    return payable_tax


def classify_charge(description):
    if "Despatch" in description:
        return "Despatch"
    elif "Return" in description:
        return "Return"
    else:
        return "Surcharge"


def order_size(description, category):
    if "Packet" in description and category == "Despatch":
        return "Packet"
    elif "Parcel" in description and category == "Despatch":
        return "Parcel"
    elif category == "Despatch":
        return "Other"
    else:
        return ""
