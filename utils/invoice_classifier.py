import pdfplumber


def invoice_detect(file_path):

    with pdfplumber.open(file_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()

    if "Evri Limited" in text:
        return "evri"
    elif "FedEx Express" in text:
        return "fedex"
    else:
        return "unknown invoice"
