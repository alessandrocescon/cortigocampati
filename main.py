# -*- coding: utf-8 -*-
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import zipfile
import ghostscript
import shutil
import os
import re
import requests
import threading
import tkinter as tk
from tkinter import filedialog

from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4, landscape
from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import Paragraph
from reportlab.platypus.tables import Table, TableStyle
import PyPDF2
from Crypto.Cipher import AES
import base64

# --- CONFIGURAZIONI DEFAULT ---
# AES-256-ECB, chiave 32 byte (PHP tronca silenziosamente i 64 char della stringa)
_KEY = b'McQfTjWnZr4u7x!a%D*G-KaPdRgUkXp2'
default_priceslevel = "pricelistbuilder"
default_vo = "400"
default_fr = "50"
default_language = "en"
default_brand = "visa"
default_name = "109000000211-001-17"
default_template = "public"
default_pricetemplate = "gross"
default_folder = "C:\\Users\\acescon\\Desktop\\LISTINO_2026\\LISTINO_2026_04\\50HZ_400V_GROSS_EN"
default_ph = 'field_gen_fas/3fn/field_gen_fas/3f/'
default_ph_val = '3'

# --- DATI GLOBALI ---
cookie_session = None
datadomain = "https://quote.visa.it"
extraparams = 'dopdf=1&action=bypass'
indexfiles = ""
indexfile_path = ""

priceslevel = default_priceslevel
vo = default_vo
fr = default_fr
language = default_language
brand = default_brand
template = default_template
pricetemplate = default_pricetemplate
distlink = "https://quote.visa.it/" + language + "/price-list-distiller&action=bypass"
savefolder = ''
finalname = ''
finalfilename = ''
finalfilenamepages = ''
phases = default_ph
ph = default_ph_val

alts = 'field_gen_alt_mod/s0l1h/field_gen_alt_mod/s0l1p/field_gen_alt_mod/s0l2g/field_gen_alt_mod/s0l2p/field_gen_alt_mod/s1l2k/field_gen_alt_mod/s1l2n/field_gen_alt_mod/s1l2y/field_gen_alt_mod/uci224g/field_gen_alt_mod/uci274c/field_gen_alt_mod/uci274e/field_gen_alt_mod/uci274f/field_gen_alt_mod/uci274g/field_gen_alt_mod/uci274h/field_gen_alt_mod/uci224e/field_gen_alt_mod/s0l1l/field_gen_alt_mod/s0l2m/field_gen_alt_mod/s4l1dd/field_gen_alt_mod/s4l1s/field_gen_alt_mod/s4l1sd/field_gen_alt_mod/ucdi274k/field_gen_alt_mod/s4l1de/field_gen_alt_mod/s4l1dg/field_gen_alt_mod/hci5f/field_gen_alt_mod/hci5c/field_gen_alt_mod/hci5d/field_gen_alt_mod/s4l1df/field_gen_alt_mod/s6l1dc/field_gen_alt_mod/s6l1dd/field_gen_alt_mod/pi734a/field_gen_alt_mod/pi734c/field_gen_alt_mod/pi734e/field_gen_alt_mod/s6l1de/field_gen_alt_mod/pi734b/field_gen_alt_mod/pi734d/field_gen_alt_mod/pi734f/field_gen_alt_mod/pi734g/field_gen_alt_mod/eco46vl4a/field_gen_alt_mod/tal044d/field_gen_alt_mod/s7l1dc/field_gen_alt_mod/s7l1dd/field_gen_alt_mod/s7l1de/field_gen_alt_mod/s7l1df/field_gen_alt_mod/s7l1dg/field_gen_alt_mod/s7l1dh/field_gen_alt_mod/s7l1dj/field_gen_alt_mod/s6l1dg/field_gen_alt_mod/s5l1dc/field_gen_alt_mod/s5l1dd/field_gen_alt_mod/s5l1df/'

pricelist_array = [
    {"link": alts+'field_gen_rng/powerfull/field_gen_vrs/b/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_emi/5/field_gen_mot_brnd/perkins/', "range": "b", "engine": "perkins", "emiss": "n2"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_vrs/b/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_brnd/fptiveco/', "range": "b", "engine": "fptiveco", "emiss": "n2"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_vrs/b/field_gen_mot_brnd/fptiveco/field_gen_mot_emi/3', "range": "b", "engine": "fptiveco", "emiss": "3"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_vrs/b/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_brnd/baudouin', "range": "b", "engine": "baudouin", "emiss": "n2"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_vrs/b/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_brnd/doosan', "range": "b", "engine": "doosan", "emiss": "n2"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_vrs/b/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_brnd/volvopenta', "range": "b", "engine": "volvopenta", "emiss": "n2"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_vrs/b/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_brnd/scania', "range": "b", "engine": "scania", "emiss": "n2"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_vrs/b/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_emi/3/field_gen_mot_brnd/yuchai', "range": "b", "engine": "yuchai", "emiss": "n2"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/u/field_gen_mot_brnd/perkins', "range": "u", "engine": "perkins", "emiss": "n2"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/u/field_gen_mot_brnd/cummins', "range": "u", "engine": "cummins", "emiss": "n2"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_emi/3/field_gen_vrs/u/field_gen_mot_brnd/yuchai', "range": "u", "engine": "yuchai", "emiss": "n2"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/u/field_gen_mot_brnd/mitsubishi', "range": "u", "engine": "mitsubishi", "emiss": "n2"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/u/field_gen_mot_brnd/baudouin', "range": "u", "engine": "baudouin", "emiss": "n2"},
    {"link": alts+'field_gen_rng/fox/field_gen_rng/bigfox/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_brnd/perkins/field_gen_vrs/fox', "range": "fox", "engine": "perkins", "emiss": "n2"},
    {"link": alts+'field_gen_rng/fox/field_gen_rng/bigfox/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_emi/3/field_gen_mot_brnd/fptiveco/field_gen_vrs/fox', "range": "fox", "engine": "fptiveco", "emiss": "n2"},
    {"link": alts+'field_gen_rng/fox/field_gen_rng/bigfox/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_emi/3/field_gen_mot_brnd/yuchai/field_gen_vrs/fox', "range": "fox", "engine": "yuchai", "emiss": "n2"},
    {"link": alts+'field_gen_rng/cricket/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_emi/5/field_gen_vrs/ck/field_gen_cof_mod/ck100100/field_gen_cof_mod/ck200200/field_gen_cof_mod/ck400000/field_gen_cof_mod/ck300000/field_gen_cof_mod/ck300100/field_gen_cof_mod/ck200100/field_gen_cof_mod/ck400000/field_gen_mot_brnd/perkins', "range": "ck", "engine": "perkins", "emiss": "n2"},
    {"link": alts+'field_gen_rng/cricket/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/ck/field_gen_cof_mod/ck100100/field_gen_cof_mod/ck200200/field_gen_cof_mod/ck400000/field_gen_cof_mod/ck300000/field_gen_cof_mod/ck300100/field_gen_cof_mod/ck200100/field_gen_cof_mod/ck400000/field_gen_mot_brnd/baudouin', "range": "ck", "engine": "baudouin", "emiss": "n2"},
    {"link": alts+'field_gen_rng/cricket/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/ck/field_gen_cof_mod/ck100100/field_gen_cof_mod/ck200200/field_gen_cof_mod/ck400000/field_gen_cof_mod/ck300000/field_gen_cof_mod/ck300100/field_gen_cof_mod/ck200100/field_gen_cof_mod/ck400000/field_gen_mot_brnd/fptiveco', "range": "ck", "engine": "fptiveco", "emiss": "n2"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/gx/field_gen_mot_brnd/perkins', "range": "gx", "engine": "perkins", "emiss": "n2"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/gx/field_gen_mot_brnd/fptiveco', "range": "gx", "engine": "fptiveco", "emiss": "n2"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_vrs/gx/field_gen_mot_brnd/fptiveco/field_gen_mot_emi/3', "range": "gx", "engine": "fptiveco", "emiss": "3"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/gx/field_gen_mot_brnd/baudouin', "range": "gx", "engine": "baudouin", "emiss": "2n"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/gx/field_gen_mot_brnd/volvopenta', "range": "gx", "engine": "volvopenta", "emiss": "2n"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_mot_emi/5/field_gen_vrs/gx/field_gen_mot_brnd/volvopenta', "range": "gx", "engine": "volvopenta", "emiss": "5"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/gx/field_gen_mot_brnd/doosan', "range": "gx", "engine": "doosan", "emiss": "2n"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/gx/field_gen_mot_brnd/scania', "range": "gx", "engine": "scania", "emiss": "2n"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_mot_emi/5/field_gen_vrs/gx/field_gen_mot_brnd/scania', "range": "gx", "engine": "scania", "emiss": "5"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/s/field_gen_mot_brnd/perkins', "range": "s", "engine": "perkins", "emiss": "2n"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/s/field_gen_mot_brnd/cummins', "range": "s", "engine": "cummins", "emiss": "2n"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/s/field_gen_mot_brnd/mitsubishi', "range": "s", "engine": "mitsubishi", "emiss": "2n"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_vrs/s/field_gen_mot_brnd/baudouin', "range": "s", "engine": "baudouin", "emiss": "2n"},
    {"link": alts+'field_gen_rng/powerfull/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_emi/3/field_gen_vrs/s/field_gen_mot_brnd/yuchai', "range": "s", "engine": "yuchai", "emiss": "2n"},
    {"link": alts+'field_gen_rng/fox/field_gen_rng/bigfox/field_gen_mot_emi/5/field_gen_vrs/fox/field_gen_mot_brnd/perkins', "range": "fox", "engine": "perkins", "emiss": "5"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_mot_emi/5/field_gen_vrs/gx/field_gen_mot_brnd/doosan', "range": "gx", "engine": "doosan", "emiss": "5"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_mot_emi/5/field_gen_vrs/gx/field_gen_mot_brnd/fptiveco', "range": "gx", "engine": "fptiveco", "emiss": "5"},
    {"link": alts+'field_gen_rng/galaxy/field_gen_mot_emi/n/field_gen_mot_emi/2/field_gen_mot_emi/3/field_gen_vrs/gx/field_gen_mot_brnd/yuchai', "range": "gx", "engine": "yuchai", "emiss": "n2"}
]

def _pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)

def make_token(path: str) -> str:
    """
    Riproduce openssl_encrypt($path, 'AES-256-ECB', $key) + double base64.
    path : stringa già nella forma attesa dal server (es. '/fileserver/...' 
           oppure '/' + filename per i doc esterni)
    """
    cipher = AES.new(_KEY, AES.MODE_ECB)
    inner = base64.b64encode(cipher.encrypt(_pkcs7_pad(path.encode())))
    return base64.b64encode(inner).decode()

# --- FUNZIONI LOGICA ---

def write_log(message):
    log_text.config(state='normal')
    log_text.insert('end', message + '\n')
    log_text.see('end')
    log_text.config(state='disabled')

def login():
    global cookie_session
    try:
        csrf_response = requests.post("https://quote.visa.it/services/session/token", verify=False)
        csrf_response.raise_for_status()
        csrf_token = csrf_response.text
    except Exception as e:
        write_log(f"Errore CSRF: {e}")
        return

    headers = {"Accept": "application/json", "X-CSRF-Token": csrf_token}
    data = {"name": "OnisVisaSpa", "pass": "LoveEyefly2016"}
    try:
        login_response = requests.post("https://quote.visa.it/rest/user/login", headers=headers, data=data, verify=False)
        login_response.raise_for_status()
        user_info = login_response.json()
        cookie_session = f"{user_info['session_name']}={user_info['sessid']}"
    except Exception as e:
        write_log(f"Errore login: {e}")

def loadfile(url, lang):
    global cookie_session, datadomain, priceslevel
    full_url = f"{datadomain}/{lang}/{priceslevel}/{url}"
    try:
        response = requests.get(full_url, headers={"Cookie": cookie_session}, verify=False, timeout=120)
        response.raise_for_status()
        html = response.text
        tables = ''
        for table_id in ['pricelist2019', 'pricelist2019extra', 'pricelist2019extras5']:
            match = re.search(rf"<table id='{table_id}'>(.*?)</table>", html, re.DOTALL)
            if match:
                tables += match.group(0)
        return tables
    except Exception as e:
        write_log(f"Errore loadfile: {e}")
        return ""

def buildpdf(htmltable, params):
    global cookie_session, distlink, savefolder, fr, vo, phases
    params['tabledata'] = htmltable
    params['voltage'] = vo
    params['frequency'] = fr
    headers = {'Cookie': cookie_session}
    try:
        response = requests.post(distlink, data=params, headers=headers, verify=False, timeout=120)
        fasi = phases.replace("field_gen_fas", "").replace("/", "")
        if response.status_code == 200:
            filename = os.path.join(savefolder, f"{params['range']}_{params['engine']}_{vo}_{fr}_{fasi}_{params['emiss']}.pdf")
            write_log(filename)
            with open(filename, 'wb') as f:
                f.write(response.content)
            write_log(f"PDF creato: {os.path.basename(filename)}")
    except Exception as e:
        write_log(f"Errore PDF: {e}")

def buildxls(htmlstr, params):
    global savefolder, fr, vo, phases
    htmlstr = htmlstr.replace(".00 €", "")
    htmlstr = re.sub(r'(?<=\d)\s+(?=\d)', '', htmlstr)
    htmlstr = htmlstr.replace("é", "&eacute;").replace("è", "&egrave;").replace("á", "&aacute;") \
                     .replace("à", "&agrave;").replace("ù", "&ugrave;").replace("ò", "&ograve;") \
                     .replace("<th", "<th bgcolor='#FFBA01'").replace("<td", "<td align='center'")
    fasi = phases.replace("field_gen_fas", "").replace("/", "")
    filename = os.path.join(savefolder, "xls", f"{params['range']}_{params['engine']}_{vo}_{fr}_{fasi}_{params['emiss']}.xls")
    write_log(filename)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(htmlstr)

def generate(item, extraparams, langu):
    global brand, template, pricetemplate, savefolder, vo, fr, phases, ph, solo_excel_var
    url = f"{phases}/{item['link']}/field_gen_freq/{fr}/field_gen_tens/{vo}?{extraparams}"
    htmltable = loadfile(url, langu)
    item.update({'language': langu, 'brand': brand, 'template': template, 'pricetemplate': pricetemplate,
                 'voltage': vo, 'frequency': fr, 'phases': ph})
    htmlstr = htmltable.replace("'", '"')

    if not solo_excel_var.get():
        buildpdf(htmlstr, item)

    buildxls(htmlstr, item)


def indice(bg, outpdf, head_text, tittext, addresstext, lefttext, righttext, r1):
    global savefolder
    pages = PdfReader(bg, decompress=False).pages
    pages = [pagexobj(pages[0])]
    canvas = Canvas(outpdf)
    canvas.setPageSize(landscape(A4))
    page_width, page_height = landscape(A4)

    canvas.doForm(makerl(canvas, pages[0]))

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.alignment = TA_JUSTIFY
    normal.fontName = "Helvetica"
    normal.fontSize = 11
    normal.textColor = "#333333"

    header = styles["Heading1"]
    header.alignment = TA_RIGHT
    header.fontName = "Helvetica"
    header.fontSize = 15
    header.textColor = "#ffffff"

    title = styles["Title"]
    title.alignment = TA_CENTER
    title.fontName = "Helvetica"
    title.fontSize = 18
    title.textColor = "#333333"

    address = styles["Heading2"]
    address.alignment = TA_CENTER
    address.fontName = "Helvetica"
    address.fontSize = 9
    address.textColor = "#333333"

    footer = styles["Heading3"]
    footer.alignment = TA_CENTER
    footer.fontName = "Helvetica"
    footer.fontSize = 9
    footer.textColor = "#333333"

    A0 = Paragraph(head_text, header)
    B0 = Paragraph('', normal)
    C0 = Paragraph('', normal)
    D0 = Paragraph('', normal)

    A1 = Paragraph('INDEX', title)
    B1 = Paragraph('', normal)
    C1 = Paragraph('', normal)
    D1 = Paragraph('', normal)

    A2 = Paragraph(lefttext, normal)
    B2 = Paragraph('', normal)
    C2 = Paragraph(righttext, normal)
    D2 = Paragraph('', normal)

    A3 = Paragraph(addresstext, footer)
    B3 = Paragraph('', normal)
    C3 = Paragraph('', normal)
    D3 = Paragraph('', normal)

    dati = [
        (A0, B0, C0, D0),
        (A1, B1, C1, D1),
        (A2, B2, C2, D2),
        (A3, B3, C3, D3)
    ]
    col_width = (page_width - 20) / 4

    tbl = Table(dati, colWidths=(col_width, col_width, col_width, col_width),
                rowHeights=(11.66*mm, 23.37*mm, float(r1)*mm, 15.50*mm))

    tbl.setStyle(TableStyle([
        ('SPAN', (0, 0), (3, 0)),
        ('TOPPADDING', (0, 0), (3, 0), 4*mm),
        ('VALIGN', (0, 0), (3, 0), 'MIDDLE'),

        ('SPAN', (0, 1), (3, 1)),
        ('VALIGN', (0, 1), (3, 1), 'MIDDLE'),

        ('SPAN', (0, 2), (1, 2)),
        ('ALIGN', (0, 2), (1, 2), 'LEFT'),
        ('VALIGN', (0, 2), (1, 2), 'TOP'),
        ('TOPPADDING', (0, 2), (1, 2), 0*mm),
        ('LEFTPADDING', (0, 2), (1, 2), 2*mm),
        ('RIGHTPADDING', (0, 2), (1, 2), 2*mm),

        ('SPAN', (2, 2), (3, 2)),
        ('ALIGN', (2, 2), (3, 2), 'LEFT'),
        ('VALIGN', (2, 2), (3, 2), 'TOP'),
        ('TOPPADDING', (2, 2), (3, 2), 0*mm),
        ('LEFTPADDING', (2, 2), (3, 2), 2*mm),
        ('RIGHTPADDING', (2, 2), (3, 2), 2*mm),

        ('SPAN', (0, 3), (3, 3)),
        ('VALIGN', (0, 3), (3, 3), 'TOP'),
        ('TOPPADDING', (0, 3), (3, 3), 3*mm),

        ('BACKGROUND', (0, 0), (-1, -1), 'transparent'),
    ]))

    tbl.wrapOn(canvas, page_width - 2*15*mm, page_height - 2*15*mm)
    tbl.drawOn(canvas, 8*mm, -84*mm)
    canvas.showPage()
    canvas.save()


def paginate():
    global language, savefolder, finalfilenamepages, indexfiles, finalfilename
    try:
        vuota_h_path = os.path.join(savefolder, "vuota_h.pdf")
        if not os.path.exists(vuota_h_path):
            write_log(f"ATTENZIONE: Il file {vuota_h_path} non esiste. Operazione interrotta.")
            return

        menu = indexfiles.strip().split('\n')
        merger = PyPDF2.PdfMerger()
        numpage = 1
        numpagei = 1
        addresst = ''

        # Costruzione colonne indice
        sxcolhtml = ''
        dxcolhtml = ''
        changecol = 38
        cr = 0

        for line in menu:
            ind = line.split(';')
            bookmarkname = ind[0]
            fname = os.path.join(savefolder, ind[1])
            txtstyle = ind[2]
            if not os.path.exists(fname):
                write_log(f"ATTENZIONE: Il file {fname} non esiste. Operazione interrotta.")
                return
            x = PdfReader(fname)
            totpagesi = len(x.pages)
            if cr <= changecol and txtstyle != 'H':
                if txtstyle == 'N':
                    sxcolhtml += "<font size=10><b>%03d</b></font>  ·  <font size=10>%s</font><br/>" % (numpagei, bookmarkname)
                    cr += 1
                elif txtstyle == 'B':
                    sxcolhtml += "<font size=10><b>%03d</b></font>  ·  <font size=10><b>%s</b></font><br/>" % (numpagei, bookmarkname)
                    cr += 1
            else:
                if txtstyle != 'H':
                    if txtstyle == 'N':
                        dxcolhtml += "<font size=10><b>%03d</b></font>  ·  <font size=10>%s</font><br/>" % (numpagei, bookmarkname)
                        cr += 1
                    elif txtstyle == 'B':
                        dxcolhtml += "<font size=10><b>%03d</b></font>  ·  <font size=10><b>%s</b></font><br/>" % (numpagei, bookmarkname)
                        cr += 1
            numpagei += totpagesi

        # Crea pagina indice
        write_log("Inizio generazione indice...")
        indice(os.path.join(savefolder, "vuota_h.pdf"),
               os.path.join(savefolder, "index.pdf"),
               '', '<b>INDEX</b>', addresst, sxcolhtml, dxcolhtml, 252.47)
        write_log("Indice generato.")

        # Merge PDF
        for line in menu:
            ind = line.split(';')
            fname = os.path.join(savefolder, ind[1])
            bookmarkname = ind[0]
            x = PdfReader(fname)
            totpages = len(x.pages)
            merger.merge(position=numpage, fileobj=open(fname, 'rb'), outline_item=bookmarkname)
            numpage += totpages

        merger.write(open(os.path.join(savefolder, finalfilename), 'wb'))

        # Numerazione pagine
        width, height = 297, 210
        firstpage = 1
        lastpage = numpage
        pgn = 1
        excl = [1, lastpage, lastpage - 1]
        pages = PdfReader(os.path.join(savefolder, finalfilename), decompress=False).pages
        pages = [pagexobj(x) for x in pages[firstpage-1:lastpage]]
        canvas = Canvas(os.path.join(savefolder, finalfilenamepages))

        for page in pages:
            canvas.setPageSize((width*mm, height*mm))
            canvas.doForm(makerl(canvas, page))
            styles = getSampleStyleSheet()
            snp = styles["Normal"]
            snp.alignment = TA_LEFT
            snp.fontName = "Helvetica"
            snp.fontSize = 11
            snp.textColor = "#333333"
            np = "<font size=11>%s</font>" % pgn
            A0 = Paragraph(np, snp)
            B0 = Paragraph('', snp)
            dati = [(A0, B0)]
            tabl = Table(dati, colWidths=(10.00, 10.00*mm), rowHeights=(10.00*mm))
            tabl.setStyle(TableStyle([
                ('SPAN', (0, 0), (1, 0)),
                ('TOPPADDING', (0, 0), (1, 0), 0*mm),
                ('VALIGN', (0, 0), (1, 0), 'BOTTOM'),
                ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                ('BACKGROUND', (0, 0), (1, 0), 'transparent'),
            ]))
            if pgn not in excl:
                tabl.wrapOn(canvas, 20.0*mm, 10.0*mm)
                tabl.drawOn(canvas, 281.0*mm, 3.0*mm)
            canvas.showPage()
            pgn += 1

        canvas.save()
        compress_pdf_final(os.path.join(savefolder, finalfilenamepages))
        write_log("PDF creato con successo!")
        zip_xls_folder()
        delete_finalfilenamepages()
        root.bell()

    except Exception as e:
        write_log(f"Errore paginate: {repr(e)}")


# --- FUNZIONI CORE GUI ---

def paginate_with_params():
    global priceslevel, vo, fr, ph, language, brand, template, pricetemplate, distlink, savefolder, indexfiles, finalname, finalfilename, finalfilenamepages, phases
    priceslevel = priceslevel_entry.get()
    vo = v_entry.get()
    fr = f_entry.get()
    ph = ph_entry.get()
    language = language_entry.get()
    distlink = f"https://quote.visa.it/{language}/price-list-distiller&action=bypass"
    brand = brand_entry.get()
    template = template_entry.get()
    pricetemplate = pricetemplate_entry.get()
    savefolder = folder_entry.get()
    phases = phases_entry.get()
    finalname = name_entry.get()
    finalfilename = finalname + ".pdf"
    finalfilenamepages = finalname + "_pages.pdf"

    if solo_impaginazione_var.get():
        # Salta generazione file, vai direttamente all'impaginazione
        copy_vuota_to_index()
        if not indexfiles.strip():
            write_log("Errore: Caricare file index.txt per la generazione PDF!")
            return
        root.after(0, paginate)
        return

    if not solo_excel_var.get():
        copy_vuota_to_index()
        if not indexfiles.strip():
            write_log("Errore: Caricare file index.txt per la generazione PDF!")
            return

    ensure_xls_folder()
    threading.Thread(target=quote_generate_thread).start()

def quote_generate_thread():
    global language
    try:
        login()
        for item in pricelist_array:
            generate(item, extraparams, language)
        if solo_excel_var.get():
            # Solo Excel: zippa e fine, senza impaginazione PDF
            zip_xls_folder()
            write_log("PROCESSO COMPLETATO (Solo Excel).")
            root.bell()
        else:
            root.after(0, paginate)
    except Exception as e:
        write_log(f"Errore nel thread: {e}")


# --- FUNZIONI UTILITY ---

def select_folder():
    f = filedialog.askdirectory()
    if f:
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, f)

def load_indexfiles_from_file():
    global indexfiles, indexfile_path
    try:
        file_path = filedialog.askopenfilename(
            title="Seleziona il file index.txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                indexfiles = f.read()
            indexfile_path = file_path
            indexfile_label.config(text=os.path.basename(file_path))
            write_log(f"File index caricato: {file_path}")
    except Exception as e:
        write_log(f"Errore caricamento file index: {e}")

def ensure_xls_folder():
    global savefolder
    xls_path = os.path.join(savefolder, "xls")
    try:
        if not os.path.exists(xls_path):
            os.makedirs(xls_path)
            write_log(f"Cartella 'xls' creata in: {xls_path}")
        else:
            for filename in os.listdir(xls_path):
                file_path = os.path.join(xls_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        import shutil as _shutil
                        _shutil.rmtree(file_path)
                except Exception as e:
                    write_log(f"Errore cancellazione {file_path}: {e}")
            write_log(f"Cartella 'xls' svuotata: {xls_path}")
    except Exception as e:
        write_log(f"Errore gestione cartella 'xls': {e}")

def zip_xls_folder():
    global savefolder, finalname
    xls_path = os.path.join(savefolder, "xls")
    zip_path = os.path.join(savefolder, finalname + '.zip')
    if not os.path.exists(xls_path):
        write_log("Cartella 'xls' non trovata.")
        return
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root_dir, dirs, files in os.walk(xls_path):
                for file in files:
                    if file.lower().endswith('.xls'):
                        file_path = os.path.join(root_dir, file)
                        arcname = os.path.relpath(file_path, xls_path)
                        zipf.write(file_path, arcname)
        write_log(f"Archivio ZIP creato: {zip_path}")
    except Exception as e:
        write_log(f"Errore creazione ZIP: {e}")

def copy_vuota_to_index():
    global savefolder
    try:
        src = os.path.join(savefolder, "vuota_h.pdf")
        dst = os.path.join(savefolder, "index.pdf")
        shutil.copyfile(src, dst)
        write_log("Copiato vuota_h.pdf su index.pdf")
    except Exception as e:
        write_log(f"Errore copia vuota_h.pdf: {e}")

def compress_pdf_final(input_file):
    global finalfilename, savefolder
    try:
        compressed_file = os.path.join(savefolder, finalfilename)
        args = [
            "-q",
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/default",
            "-dColorImageDownsampleType=/Bicubic",
            "-dColorImageResolution=150",
            "-dGrayImageDownsampleType=/Bicubic",
            "-dGrayImageResolution=150",
            "-dMonoImageDownsampleType=/Subsample",
            "-dMonoImageResolution=150",
            "-dJPEGQ=85",
            "-sOutputFile=" + compressed_file,
            input_file
        ]
        ghostscript.Ghostscript(*args)
        write_log(f"Compressione completata: {compressed_file}")
        filenamepdf = "/fileserver/109_Documenti_Commerciali/"+finalname+'.pdf'
        tokenpdf = make_token(filenamepdf)
        urlpdf = "https://www.visa.it"+filenamepdf+"?token="+tokenpdf
        write_log(f"File URL: {urlpdf}")
        filenamezip = "/fileserver/109_Documenti_Commerciali/"+finalname+'.zip'
        tokenzip = make_token(filenamezip)
        urlzip = "https://www.visa.it"+filenamezip+"?token="+tokenzip
        write_log(f"File URL: {urlzip}")


    except Exception as e:
        write_log(f"Errore durante la compressione: {e}")

def delete_finalfilenamepages():
    global finalfilenamepages, savefolder
    filepath = os.path.join(savefolder, finalfilenamepages)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            write_log(f"File temporaneo cancellato: {filepath}")
        else:
            write_log(f"File non trovato: {filepath}")
    except Exception as e:
        write_log(f"Errore cancellazione {filepath}: {e}")


# --- INTERFACCIA GRAFICA ---

root = tk.Tk()
root.title("Visa Pricelist Generator 2026")
root.geometry("800x750")

fields = [
    ("Prices Level:", "priceslevel_entry", default_priceslevel),
    ("V (Voltage):", "v_entry", default_vo),
    ("F (Frequency):", "f_entry", default_fr),
    ("P (Phases):", "ph_entry", default_ph_val),
    ("Phases string:", "phases_entry", default_ph),
    ("Language:", "language_entry", default_language),
    ("Brand:", "brand_entry", default_brand),
    ("Template:", "template_entry", default_template),
    ("Price Template:", "pricetemplate_entry", default_pricetemplate),
    ("File name:", "name_entry", default_name),
]

entries = {}
for txt, var_name, dval in fields:
    tk.Label(root, text=txt).pack()
    ent = tk.Entry(root)
    ent.insert(0, dval)
    ent.pack()
    entries[var_name] = ent

priceslevel_entry = entries["priceslevel_entry"]
v_entry           = entries["v_entry"]
f_entry           = entries["f_entry"]
ph_entry          = entries["ph_entry"]
phases_entry      = entries["phases_entry"]
language_entry    = entries["language_entry"]
brand_entry       = entries["brand_entry"]
template_entry    = entries["template_entry"]
pricetemplate_entry = entries["pricetemplate_entry"]
name_entry        = entries["name_entry"]

tk.Label(root, text="Default folder:").pack()
f_frame = tk.Frame(root)
f_frame.pack()
folder_entry = tk.Entry(f_frame, width=50)
folder_entry.insert(0, default_folder)
folder_entry.pack(side=tk.LEFT)
tk.Button(f_frame, text="...", command=select_folder).pack(side=tk.LEFT)

tk.Button(root, text="Carica Index.txt", command=load_indexfiles_from_file).pack(pady=5)
indexfile_label = tk.Label(root, text="Nessun file caricato", fg="blue")
indexfile_label.pack()

# Flag SOLO EXCEL
solo_excel_var = tk.BooleanVar(value=False)
tk.Checkbutton(root, text="SOLO EXCEL (Salva tempo, no PDF)", variable=solo_excel_var,
               font=("Arial", 11, "bold"), fg="red").pack(pady=(10, 2))

# Flag SOLO IMPAGINAZIONE
solo_impaginazione_var = tk.BooleanVar(value=False)
tk.Checkbutton(root, text="SOLO IMPAGINAZIONE PDF (Usa file già generati)", variable=solo_impaginazione_var,
               font=("Arial", 11, "bold"), fg="blue").pack(pady=(2, 10))

tk.Button(root, text="GENERA ORA", font=("Arial", 14, "bold"), bg="#4CAF50", fg="white",
          command=paginate_with_params).pack(pady=10)

# Log
log_frame = tk.Frame(root)
log_frame.pack(pady=10, fill=tk.BOTH, expand=True)
log_text = tk.Text(log_frame, height=15, state='disabled')
log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
sb = tk.Scrollbar(log_frame, command=log_text.yview)
sb.pack(side=tk.RIGHT, fill=tk.Y)
log_text.config(yscrollcommand=sb.set)

root.mainloop()