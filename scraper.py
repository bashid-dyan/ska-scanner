import requests
from bs4 import BeautifulSoup
import re

BASE_URL = 'https://cekskk.com'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
}

_session = requests.Session()
_session.headers.update(HEADERS)


def search_tenaga_kerja(keyword, search_type='Nama'):
    """Search tenaga kerja via cekskk.com"""
    if search_type == 'NIK':
        url = f'{BASE_URL}/tracking/ska?via=nik&p={keyword}'
    else:
        url = f'{BASE_URL}/tracking/ska?via=nama&p={keyword}'

    r = _session.get(url, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, 'lxml')
    results = []

    # Find all detail links
    links = soup.select('a[href*="tenaga-kerja-konstruksi"]')

    for link in links:
        href = link.get('href', '')
        if not href or 'Detail' not in link.get_text():
            continue

        # Get parent card/row to extract name and NIK
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
            # Location patterns
            if any(x in line for x in ['Kab.', 'Kota ', 'Provinsi']):
                lokasi = line

        # Extract detail path
        detail_path = href if href.startswith('/') else f'/{href}'

        results.append({
            'nama': nama,
            'nik': nik,
            'lokasi': lokasi,
            'detail_url': detail_path,
        })

    # Get total count
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
    r = _session.get(url, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, 'lxml')

    # Extract profile info
    profile = _extract_profile(soup)

    # Extract certificates (SKK, SKA, SKT)
    certificates = _extract_certificates(soup)

    return {
        'profil': profile,
        'sertifikat': certificates,
        'source_url': url,
    }


def _extract_profile(soup):
    """Extract profile information from detail page"""
    profile = {}

    # Get name from h1/h2
    name_el = soup.select_one('h1, h2')
    if name_el:
        profile['nama'] = name_el.get_text(strip=True)

    # Look for NIK
    nik_pattern = re.compile(r'NIK[:\s]*(\d{8,}[\dxX]*)', re.IGNORECASE)
    text = soup.get_text()
    nik_match = nik_pattern.search(text)
    if nik_match:
        profile['nik'] = nik_match.group(1)

    # Look for education
    edu_match = re.search(r'Pendidikan[:\s]*([^\n<]+)', text)
    if edu_match:
        profile['pendidikan'] = edu_match.group(1).strip()

    # Total certificates
    cert_match = re.search(r'Total Sertifikat[:\s]*(\d+)', text)
    if cert_match:
        profile['total_sertifikat'] = int(cert_match.group(1))

    return profile


def _extract_certificates(soup):
    """Extract all certificate data from the detail page"""
    certificates = []

    # Find all card-body elements that contain certificate info
    cards = soup.select('.card-body')

    for card in cards:
        text = card.get_text('\n', strip=True)

        # Skip non-certificate cards (ads, promotions, profile sections)
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

        # Certificate title (first significant text)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            continue

        # Try to identify certificate type
        if any(x in text for x in ['SKK Konstruksi', 'Jenjang:', 'Penerbit:']):
            cert['tipe'] = 'SKK Konstruksi'
        elif 'SKA' in text:
            cert['tipe'] = 'SKA'
        elif 'SKT' in text:
            cert['tipe'] = 'SKT'
        else:
            continue

        cert['judul'] = lines[0] if lines else ''

        # Extract status
        if 'Berlaku' in text and 'Tidak Berlaku' not in text:
            cert['status'] = 'Berlaku'
        elif 'Tidak Berlaku' in text or 'Expired' in text:
            cert['status'] = 'Tidak Berlaku'
        else:
            cert['status'] = '-'

        # Extract fields using patterns
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
