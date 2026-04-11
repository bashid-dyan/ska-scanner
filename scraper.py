import requests
from bs4 import BeautifulSoup
import re
import time

BASE_URL = 'https://cekskk.com'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
}

_session = requests.Session()
_session.headers.update(HEADERS)

MAX_RETRIES = 3
RETRY_DELAY = 2


def _fetch(url, retries=MAX_RETRIES):
    """Fetch URL with retry logic."""
    for attempt in range(retries):
        try:
            r = _session.get(url, timeout=30)
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise e


# ============================================================
# TENAGA KERJA (Workers)
# ============================================================

def search_tenaga_kerja(keyword, search_type='Nama'):
    """Search tenaga kerja via cekskk.com"""
    if search_type == 'NIK':
        url = f'{BASE_URL}/tracking/ska?via=nik&p={keyword}'
    else:
        url = f'{BASE_URL}/tracking/ska?via=nama&p={keyword}'

    r = _fetch(url)
    soup = BeautifulSoup(r.text, 'lxml')
    results = []

    links = soup.select('a[href*="tenaga-kerja-konstruksi"]')

    for link in links:
        href = link.get('href', '')
        if not href or 'Detail' not in link.get_text():
            continue

        parent = link.find_parent('div', class_='card') or link.find_parent('div')
        if not parent:
            continue

        text = parent.get_text('\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        nama = lines[0] if lines else ''
        nik = ''
        lokasi = ''

        for line in lines:
            if re.match(r'^\d{8,}', line):
                nik = line
            if any(x in line for x in ['Kab.', 'Kota ', 'Provinsi']):
                lokasi = line

        detail_path = href if href.startswith('/') else f'/{href}'

        results.append({
            'nama': nama,
            'nik': nik,
            'lokasi': lokasi,
            'detail_url': detail_path,
        })

    total_text = soup.get_text()
    total_match = re.search(r'(\d+)\s*Hasil Pencarian', total_text)
    total = int(total_match.group(1)) if total_match else len(results)

    return {
        'results': results,
        'total': total,
        'keyword': keyword,
        'type': search_type,
    }


def get_detail(detail_path):
    """Get full detail of a tenaga kerja from cekskk.com"""
    url = f'{BASE_URL}{detail_path}'
    r = _fetch(url)
    soup = BeautifulSoup(r.text, 'lxml')

    profile = _extract_profile(soup)
    certificates = _extract_certificates(soup)

    return {
        'profil': profile,
        'sertifikat': certificates,
        'source_url': url,
    }


# ============================================================
# BADAN USAHA (Business Entities)
# ============================================================

def search_badan_usaha(keyword, search_type='Nama'):
    """Search badan usaha konstruksi via cekskk.com"""
    if search_type == 'NPWP':
        url = f'{BASE_URL}/tracking/sbu?via=npwp&p={keyword}'
    else:
        url = f'{BASE_URL}/tracking/sbu?via=nama&p={keyword}'

    r = _fetch(url)
    soup = BeautifulSoup(r.text, 'lxml')
    results = []

    links = soup.select('a[href*="badan-usaha"]')

    for link in links:
        href = link.get('href', '')
        if not href or 'Detail' not in link.get_text():
            continue

        parent = link.find_parent('div', class_='card') or link.find_parent('div')
        if not parent:
            continue

        text = parent.get_text('\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        nama = lines[0] if lines else ''
        npwp = ''
        lokasi = ''

        for line in lines:
            # NPWP pattern: digits with dots and dashes (e.g., 01.234.567.8-901.000)
            if re.match(r'^[\d]{2}\.[\d]{3}\.[\d]{3}', line) or re.match(r'^\d{10,}', line):
                npwp = line
            if any(x in line for x in ['Kab.', 'Kota ', 'Provinsi']):
                lokasi = line

        detail_path = href if href.startswith('/') else f'/{href}'

        results.append({
            'nama': nama,
            'npwp': npwp,
            'lokasi': lokasi,
            'detail_url': detail_path,
        })

    total_text = soup.get_text()
    total_match = re.search(r'(\d+)\s*Hasil Pencarian', total_text)
    total = int(total_match.group(1)) if total_match else len(results)

    return {
        'results': results,
        'total': total,
        'keyword': keyword,
        'type': search_type,
    }


def get_detail_badan_usaha(detail_path):
    """Get full detail of a badan usaha from cekskk.com"""
    url = f'{BASE_URL}{detail_path}'
    r = _fetch(url)
    soup = BeautifulSoup(r.text, 'lxml')

    profile = _extract_profile_bu(soup)
    sbu_list = _extract_sbu(soup)

    return {
        'profil': profile,
        'sbu': sbu_list,
        'source_url': url,
    }


# ============================================================
# EXTRACTION HELPERS
# ============================================================

def _extract_profile(soup):
    """Extract profile information from tenaga kerja detail page"""
    profile = {}

    name_el = soup.select_one('h1, h2')
    if name_el:
        profile['nama'] = name_el.get_text(strip=True)

    text = soup.get_text()

    nik_match = re.search(r'NIK[:\s]*(\d{8,}[\dxX]*)', text, re.IGNORECASE)
    if nik_match:
        profile['nik'] = nik_match.group(1)

    edu_match = re.search(r'Pendidikan[:\s]*([^\n<]+)', text)
    if edu_match:
        profile['pendidikan'] = edu_match.group(1).strip()

    cert_match = re.search(r'Total Sertifikat[:\s]*(\d+)', text)
    if cert_match:
        profile['total_sertifikat'] = int(cert_match.group(1))

    return profile


def _extract_profile_bu(soup):
    """Extract profile information from badan usaha detail page"""
    profile = {}

    name_el = soup.select_one('h1, h2')
    if name_el:
        profile['nama'] = name_el.get_text(strip=True)

    text = soup.get_text()

    npwp_match = re.search(r'NPWP[:\s]*([\d.\-]+)', text, re.IGNORECASE)
    if npwp_match:
        profile['npwp'] = npwp_match.group(1)

    alamat_match = re.search(r'Alamat[:\s]*([^\n<]+)', text, re.IGNORECASE)
    if alamat_match:
        profile['alamat'] = alamat_match.group(1).strip()

    nib_match = re.search(r'NIB[:\s]*([\d]+)', text, re.IGNORECASE)
    if nib_match:
        profile['nib'] = nib_match.group(1)

    telp_match = re.search(r'(?:Telp|Telepon|Phone)[:\s]*([\d\-\+\s]+)', text, re.IGNORECASE)
    if telp_match:
        profile['telepon'] = telp_match.group(1).strip()

    email_match = re.search(r'Email[:\s]*([\w\.\-]+@[\w\.\-]+)', text, re.IGNORECASE)
    if email_match:
        profile['email'] = email_match.group(1)

    sbu_count = re.search(r'Total\s*(?:SBU|Sertifikat)[:\s]*(\d+)', text, re.IGNORECASE)
    if sbu_count:
        profile['total_sbu'] = int(sbu_count.group(1))

    return profile


def _extract_sbu(soup):
    """Extract SBU (Sertifikat Badan Usaha) data from detail page"""
    sbu_list = []
    cards = soup.select('.card-body')

    for card in cards:
        text = card.get_text('\n', strip=True)

        if any(skip in text for skip in [
            'Tentang', 'Sponsored', 'Perpanjangan', 'Whatsapp',
            'Hubungi kami', 'Konsultasi', 'Pelatihan',
        ]):
            continue
        if len(text) < 20:
            continue

        sbu = {}

        if not any(x in text for x in ['SBU', 'Klasifikasi', 'Kualifikasi', 'Sub Bidang']):
            continue

        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            continue

        sbu['judul'] = lines[0]

        if 'Berlaku' in text and 'Tidak Berlaku' not in text:
            sbu['status'] = 'Berlaku'
        elif 'Tidak Berlaku' in text or 'Expired' in text:
            sbu['status'] = 'Tidak Berlaku'
        else:
            sbu['status'] = '-'

        patterns = {
            'klasifikasi': r'Klasifikasi[:\s]*([^\n]+)',
            'kualifikasi': r'Kualifikasi[:\s]*([^\n]+)',
            'sub_bidang': r'Sub Bidang[:\s]*([^\n]+)',
            'nomor_registrasi': r'No\.\s*(?:Registrasi|SBU)[:\s]*([^\n]+)',
            'berlaku_hingga': r'Berlaku hingga[:\s]*([^\n]+)',
            'penerbit': r'Penerbit[:\s]*([^\n]+)',
            'asosiasi': r'Asosiasi[:\s]*([^\n]+)',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sbu[key] = match.group(1).strip()

        if sbu.get('judul'):
            sbu_list.append(sbu)

    return sbu_list


def _extract_certificates(soup):
    """Extract all certificate data from the detail page"""
    certificates = []

    cards = soup.select('.card-body')

    for card in cards:
        text = card.get_text('\n', strip=True)

        if any(skip in text for skip in [
            'Tentang Profil', 'Sponsored', 'Perpanjangan SKK',
            'Lindungi SKK', 'Pelatihan &', 'Konsultasi di',
            'Whatsapp', 'Hubungi kami', 'Utilitas Software',
            'SKA/SKT Anda Expired', 'Jangan Khawatir',
            'Gunakan layanan perpanjangan',
        ]):
            continue
        if len(text) < 20:
            continue

        cert = {}

        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            continue

        if any(x in text for x in ['SKK Konstruksi', 'Jenjang:', 'Penerbit:']):
            cert['tipe'] = 'SKK Konstruksi'
        elif 'SKA' in text:
            cert['tipe'] = 'SKA'
        elif 'SKT' in text:
            cert['tipe'] = 'SKT'
        else:
            continue

        cert['judul'] = lines[0] if lines else ''

        if 'Berlaku' in text and 'Tidak Berlaku' not in text:
            cert['status'] = 'Berlaku'
        elif 'Tidak Berlaku' in text or 'Expired' in text:
            cert['status'] = 'Tidak Berlaku'
        else:
            cert['status'] = '-'

        patterns = {
            'jenjang': r'Jenjang[:\s]*(\S+)',
            'penerbit': r'Penerbit[:\s]*([^\n]+)',
            'asosiasi': r'Asosiasi[:\s]*([^\n]+)',
            'registrasi': r'Registrasi[:\s]*([^\n]+)',
            'berlaku_hingga': r'Berlaku hingga[:\s]*([^\n]+)',
            'sub_bidang': r'Sub Bidang[:\s]*([^\n]+)',
            'klasifikasi': r'Klasifikasi[:\s]*([^\n]+)',
            'kualifikasi': r'Kualifikasi[:\s]*([^\n]+)',
            'nomor_registrasi': r'No\.\s*Registrasi[:\s]*([^\n]+)',
            'tanggal_cetak': r'Tanggal Cetak[:\s]*([^\n]+)',
            'masa_berlaku': r'Masa berlaku[:\s]*([^\n]+)',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cert[key] = match.group(1).strip()

        if cert.get('judul'):
            certificates.append(cert)

    return certificates


def close():
    """Close session"""
    _session.close()
