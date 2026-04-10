from flask import Flask, request, jsonify, render_template
import scraper
import cache
import atexit

app = Flask(__name__, template_folder='templates', static_folder='static')

SEARCH_CACHE_TTL = 300      # 5 menit
DETAIL_CACHE_TTL = 3600     # 1 jam


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'Nama')

    if not q:
        return jsonify({'error': 'Parameter q (keyword) harus diisi'}), 400

    if search_type not in ('Nama', 'NIK'):
        return jsonify({'error': 'Parameter type harus Nama atau NIK'}), 400

    cache_key = f'search:{search_type}:{q}'
    cached = cache.get(cache_key, SEARCH_CACHE_TTL)
    if cached:
        cached['from_cache'] = True
        return jsonify(cached)

    try:
        result = scraper.search_tenaga_kerja(q, search_type)
        cache.set(cache_key, result)
        result['from_cache'] = False
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detail')
def api_detail():
    path = request.args.get('path', '').strip()
    if not path:
        return jsonify({'error': 'Parameter path harus diisi'}), 400

    cache_key = f'detail:{path}'
    cached = cache.get(cache_key, DETAIL_CACHE_TTL)
    if cached:
        return jsonify(cached)

    try:
        result = scraper.get_detail(path)
        cache.set(cache_key, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@atexit.register
def cleanup():
    scraper.close()


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 3000))
    print(f'=== SKA Scanner by Bashid Effendi ===')
    print(f'Server berjalan di http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
