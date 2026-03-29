from datetime import date
from flask import Blueprint, jsonify, request
from app import db
from app.models import Session, Curriculum, CurriculumItem
from app.utils.stats import get_heatmap_data, get_velocity, get_projected_completion

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/heatmap')
def heatmap():
    return jsonify(get_heatmap_data())


@api_bp.route('/heatmap/<int:curriculum_id>')
def heatmap_curriculum(curriculum_id):
    return jsonify(get_heatmap_data(curriculum_id=curriculum_id))


@api_bp.route('/items')
def items():
    """Return items for a curriculum (for dynamic dropdowns)."""
    curriculum_id = request.args.get('curriculum_id', type=int)
    if not curriculum_id:
        return jsonify([])
    items = (
        CurriculumItem.query
        .filter_by(curriculum_id=curriculum_id, deleted=False, completed=False)
        .order_by(CurriculumItem.sort_order, CurriculumItem.id)
        .all()
    )
    return jsonify([{'id': i.id, 'title': i.title} for i in items])


@api_bp.route('/sessions/stop', methods=['POST'])
def stop_timer():
    data = request.get_json(silent=True) or {}
    curriculum_id = data.get('curriculum_id')
    duration_minutes = data.get('duration_minutes')
    note = data.get('note', '') or None
    item_id = data.get('item_id') or None
    client_date = data.get('date')

    curriculum = Curriculum.query.get(curriculum_id) if curriculum_id else None
    if not curriculum or not duration_minutes or int(duration_minutes) <= 0:
        return jsonify({'error': 'Invalid data'}), 400

    try:
        logged_at = date.fromisoformat(client_date) if client_date else date.today()
    except ValueError:
        logged_at = date.today()

    s = Session(
        curriculum_id=curriculum_id,
        item_id=item_id,
        duration_minutes=int(duration_minutes),
        logged_at=logged_at,
        note=note,
        source='timer'
    )
    db.session.add(s)
    db.session.commit()

    return jsonify({
        'status': 'ok',
        'session_id': s.id,
        'total_hours': round(curriculum.total_hours, 2),
        'progress_pct': round(curriculum.progress_pct, 1)
    })


@api_bp.route('/stats')
def stats():
    curricula = Curriculum.query.filter_by(archived=False).all()
    result = []
    for c in curricula:
        velocity = get_velocity(c)
        projected = get_projected_completion(c)
        result.append({
            'id': c.id,
            'name': c.name,
            'total_hours': round(c.total_hours, 1),
            'mastery_hours': c.mastery_hours,
            'progress_pct': round(c.progress_pct, 1),
            'velocity_h_per_day': round(velocity, 2),
            'projected_completion': projected.isoformat() if projected else None
        })
    return jsonify(result)
