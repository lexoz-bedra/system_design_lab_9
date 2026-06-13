import os
import threading
from flask import Blueprint, request, jsonify, render_template

from .downloader import download_quarter, AVAILABLE_YEARS, QUARTERS
from .pipeline_steps import run_pipeline
from .duck_pipeline import get_stats
from .data_pipeline import load_file, preprocess, get_stats as get_stats_pandas, UPLOAD_FOLDER
from .model import train, predict, is_trained
from .zones import ZONE_CSV, ensure_downloaded
from .charts import (
    chart_hourly_trips,
    chart_fare_distribution,
    chart_top_zones,
    chart_feature_importance,
    chart_heatmap,
    chart_revenue_zones,
)

bp = Blueprint('main', __name__)

_state = {
    'filepath': None,
    'df': None,
    'stats': None,
    'metrics': None,
    'training': False,
    'downloading': False,
    'download_progress': 0,
    'download_month_idx': 0,
    'pipeline_running': False,
    'pipeline_steps': [],
    'error': None,
}


def _run_pipeline_bg():
    _state['pipeline_running'] = True
    _state['pipeline_steps'] = []
    try:
        def on_step(result):
            _state['pipeline_steps'].append(result)

        steps, df = run_pipeline(_state['filepath'], on_step=on_step)
        _state['df'] = df
        _state['stats'] = get_stats(df)
        _state['metrics'] = None
        _state['error'] = None
    except Exception as e:
        _state['error'] = str(e)
    finally:
        _state['pipeline_running'] = False


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/api/periods')
def periods():
    return jsonify({
        'years': AVAILABLE_YEARS,
        'quarters': [{'value': q, 'label': f'Q{q} (месяцы {m[0]}–{m[-1]})'} for q, m in QUARTERS.items()],
    })


@bp.route('/api/download', methods=['POST'])
def download_data():
    body = request.get_json(force=True)
    year = int(body.get('year', 0))
    quarter = int(body.get('quarter', 0))

    if year not in AVAILABLE_YEARS or quarter not in QUARTERS:
        return jsonify({'error': 'Invalid year or quarter'}), 400
    if _state['downloading']:
        return jsonify({'error': 'Download already in progress'}), 409

    def run():
        _state['downloading'] = True
        _state['download_progress'] = 0
        _state['download_month_idx'] = 0
        _state['error'] = None
        try:
            months = QUARTERS[quarter]

            def on_progress(month_idx, done, total):
                base = month_idx * 100 // len(months)
                chunk = done / total * 100 // len(months) if total else 0
                _state['download_progress'] = round(base + chunk)
                _state['download_month_idx'] = month_idx

            filepaths = download_quarter(year, quarter, on_progress=on_progress)
            _state['download_progress'] = 100
            _state['filepath'] = filepaths
        except Exception as e:
            _state['error'] = str(e)
        finally:
            _state['downloading'] = False

        if not _state['error']:
            _run_pipeline_bg()

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'success': True})


@bp.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    _state['filepath'] = filepath
    _state['error'] = None

    threading.Thread(target=_run_pipeline_bg, daemon=True).start()
    return jsonify({'success': True})


@bp.route('/api/pipeline/status')
def pipeline_status():
    return jsonify({
        'running': _state['pipeline_running'],
        'steps': _state['pipeline_steps'],
        'done': not _state['pipeline_running'] and len(_state['pipeline_steps']) > 0,
        'error': _state['error'],
    })


@bp.route('/api/status')
def status():
    return jsonify({
        'data_loaded': _state['df'] is not None,
        'stats': _state['stats'],
        'training': _state['training'],
        'downloading': _state['downloading'],
        'download_progress': _state['download_progress'],
        'pipeline_running': _state['pipeline_running'],
        'pipeline_steps_count': len(_state['pipeline_steps']),
        'metrics': _state['metrics'],
        'model_ready': is_trained(),
        'error': _state['error'],
    })


@bp.route('/api/train', methods=['POST'])
def train_model():
    if _state['df'] is None:
        return jsonify({'error': 'No data loaded'}), 400
    if _state['training']:
        return jsonify({'error': 'Training already in progress'}), 409

    def run_training():
        _state['training'] = True
        try:
            metrics = train(_state['df'])
            _state['metrics'] = metrics
            _state['error'] = None
        except Exception as e:
            _state['error'] = str(e)
        finally:
            _state['training'] = False

    threading.Thread(target=run_training, daemon=True).start()
    return jsonify({'success': True})


@bp.route('/api/charts/hourly')
def chart_hourly():
    if _state['df'] is None:
        return jsonify({'error': 'No data'}), 400
    try:
        return jsonify(chart_hourly_trips(_state['df']))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/charts/fare_dist')
def chart_fare_dist():
    if _state['df'] is None:
        return jsonify({'error': 'No data'}), 400
    try:
        return jsonify(chart_fare_distribution(_state['df']))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/charts/top_zones')
def chart_zones():
    if _state['df'] is None:
        return jsonify({'error': 'No data'}), 400
    try:
        return jsonify(chart_top_zones(_state['df']))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/charts/feature_importance')
def chart_importance():
    if _state['metrics'] is None:
        return jsonify({'error': 'Model not trained yet'}), 400
    try:
        return jsonify(chart_feature_importance(_state['metrics']['feature_importance']))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/charts/heatmap')
def chart_heatmap_route():
    if _state['df'] is None:
        return jsonify({'error': 'No data'}), 400
    try:
        return jsonify(chart_heatmap(_state['df']))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/charts/revenue_zones')
def chart_revenue_route():
    if _state['df'] is None:
        return jsonify({'error': 'No data'}), 400
    try:
        return jsonify(chart_revenue_zones(_state['df']))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/zones')
def zones():
    import csv
    ensure_downloaded()
    try:
        with open(ZONE_CSV, newline='', encoding='utf-8') as f:
            rows = [r for r in csv.DictReader(f)]
        return jsonify([
            {'id': int(r['LocationID']), 'label': f"{r['Zone']}, {r['Borough']}"}
            for r in sorted(rows, key=lambda r: r['Zone'])
        ])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/predict', methods=['POST'])
def predict_fare():
    if not is_trained():
        return jsonify({'error': 'Модель не обучена'}), 400
    try:
        body = request.get_json(force=True)
        fare = predict(body)
        return jsonify({'fare': round(fare, 2)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
