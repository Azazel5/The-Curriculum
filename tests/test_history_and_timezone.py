import os
import tempfile
import unittest
from datetime import date, datetime
from unittest.mock import patch

from app import create_app, db
from app.models import Curriculum, CurriculumItem, Session, Settings, User
from app.utils.dates import local_today


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test-secret'
    WTF_CSRF_ENABLED = False


class HistoryAndTimezoneTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        TestConfig.SQLALCHEMY_DATABASE_URI = f'sqlite:///{self.db_path}'
        TestConfig.SQLALCHEMY_ENGINE_OPTIONS = {'connect_args': {'check_same_thread': False}}
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.user = User(email='test@example.com', password_hash='x', is_guest=False)
        db.session.add(self.user)
        db.session.flush()
        db.session.add(Settings(user_id=self.user.id, timezone='America/New_York'))
        self.curriculum = Curriculum(
            user_id=self.user.id,
            name='Mechanistic Interpretability',
            mastery_hours=10,
            color='#22c55e',
        )
        db.session.add(self.curriculum)
        db.session.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['_user_id'] = str(self.user.id)
            session['_fresh'] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        os.unlink(self.db_path)

    def test_local_today_uses_user_timezone(self):
        utc_now = datetime(2026, 4, 29, 3, 30, 0)
        self.assertEqual(local_today('America/New_York', now=utc_now), date(2026, 4, 28))
        self.assertEqual(local_today('UTC', now=utc_now), date(2026, 4, 29))

    def test_log_page_renders_recurring_and_one_time_items_for_selected_curriculum(self):
        item = CurriculumItem(
            curriculum_id=self.curriculum.id,
            title='Activation Patching',
            item_kind=CurriculumItem.KIND_DAILY,
            completion_style=CurriculumItem.STYLE_TIME_THRESHOLD,
            daily_target_minutes=30,
        )
        one_time = CurriculumItem(
            curriculum_id=self.curriculum.id,
            title='Set Up LLC',
            item_kind=CurriculumItem.KIND_ONE_SHOT,
            completion_style=CurriculumItem.STYLE_PRESENCE,
            one_time_target_minutes=120,
        )
        db.session.add(item)
        db.session.add(one_time)
        db.session.commit()

        response = self.client.get(f'/log?curriculum={self.curriculum.id}')
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Activation Patching', body)
        self.assertIn('Set Up LLC', body)
        self.assertIn('<select name="item_id" id="manual-item"', body)

    def test_one_time_item_completes_from_total_minutes(self):
        item = CurriculumItem(
            curriculum_id=self.curriculum.id,
            title='Set Up Business Process',
            item_kind=CurriculumItem.KIND_ONE_SHOT,
            completion_style=CurriculumItem.STYLE_PRESENCE,
            one_time_target_minutes=90,
        )
        db.session.add(item)
        db.session.flush()
        db.session.add(Session(
            curriculum_id=self.curriculum.id,
            item_id=item.id,
            duration_minutes=60,
            logged_at=date(2026, 4, 28),
            source='manual',
        ))
        db.session.add(Session(
            curriculum_id=self.curriculum.id,
            item_id=item.id,
            duration_minutes=30,
            logged_at=date(2026, 4, 29),
            source='timer',
        ))
        db.session.commit()
        self.assertTrue(item.is_one_shot_done)
        self.assertTrue(item.is_complete_for_stats(date(2026, 4, 29)))

    def test_history_csv_includes_notes_and_progress(self):
        db.session.add_all([
            Session(
                curriculum_id=self.curriculum.id,
                duration_minutes=60,
                logged_at=date(2026, 4, 28),
                note='Read papers',
                source='manual',
            ),
            Session(
                curriculum_id=self.curriculum.id,
                duration_minutes=30,
                logged_at=date(2026, 4, 29),
                note='Implemented dashboard fix',
                source='timer',
            ),
        ])
        db.session.commit()

        with patch('app.routes.sessions.local_today_for_user', return_value=date(2026, 4, 30)):
            response = self.client.get('/history?format=csv')
            body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('curriculum-history.csv', response.headers.get('Content-Disposition', ''))
        self.assertIn('Read papers', body)
        self.assertIn('Implemented dashboard fix', body)
        self.assertIn('Mechanistic Interpretability', body)
        self.assertIn('15.0', body)

    def test_history_defaults_to_month_to_date(self):
        db.session.add_all([
            Session(
                curriculum_id=self.curriculum.id,
                duration_minutes=10,
                logged_at=date(2026, 3, 31),
                note='March',
                source='manual',
            ),
            Session(
                curriculum_id=self.curriculum.id,
                duration_minutes=20,
                logged_at=date(2026, 4, 2),
                note='April',
                source='manual',
            ),
        ])
        db.session.commit()

        with patch('app.routes.sessions.local_today_for_user', return_value=date(2026, 4, 15)):
            response = self.client.get('/history')
            body = response.get_data(as_text=True)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('March', body)
            self.assertIn('April', body)

    def test_history_range_filter_applies_to_csv(self):
        db.session.add_all([
            Session(curriculum_id=self.curriculum.id, duration_minutes=10, logged_at=date(2026, 4, 1), note='A', source='manual'),
            Session(curriculum_id=self.curriculum.id, duration_minutes=10, logged_at=date(2026, 4, 10), note='B', source='manual'),
            Session(curriculum_id=self.curriculum.id, duration_minutes=10, logged_at=date(2026, 4, 20), note='C', source='manual'),
        ])
        db.session.commit()
        response = self.client.get('/history?format=csv&start=2026-04-05&end=2026-04-15')
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(',A,', body)
        self.assertIn(',B,', body)
        self.assertNotIn(',C,', body)

    def test_completed_items_count_uses_local_today(self):
        item = CurriculumItem(
            curriculum_id=self.curriculum.id,
            title='Circuit Discovery',
            item_kind=CurriculumItem.KIND_DAILY,
            completion_style=CurriculumItem.STYLE_TIME_THRESHOLD,
            daily_target_minutes=30,
        )
        db.session.add(item)
        db.session.flush()
        db.session.add(Session(
            curriculum_id=self.curriculum.id,
            item_id=item.id,
            duration_minutes=30,
            logged_at=date(2026, 4, 28),
            source='manual',
        ))
        db.session.commit()

        with patch('app.models.local_today_for_user', return_value=date(2026, 4, 28)):
            self.assertEqual(self.curriculum.completed_items_count, 1)

    def test_api_items_includes_one_time_item(self):
        db.session.add(CurriculumItem(
            curriculum_id=self.curriculum.id,
            title='Recurring Practice',
            item_kind=CurriculumItem.KIND_DAILY,
            completion_style=CurriculumItem.STYLE_TIME_THRESHOLD,
            daily_target_minutes=30,
            deadline=date(2026, 5, 5),
        ))
        db.session.add(CurriculumItem(
            curriculum_id=self.curriculum.id,
            title='One-time Milestone',
            item_kind=CurriculumItem.KIND_ONE_SHOT,
            completion_style=CurriculumItem.STYLE_PRESENCE,
            one_time_target_minutes=120,
            deadline=date(2026, 4, 30),
        ))
        db.session.commit()
        response = self.client.get(f'/api/items?curriculum_id={self.curriculum.id}')
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        titles = [row['title'] for row in payload]
        self.assertIn('Recurring Practice', titles)
        self.assertIn('One-time Milestone', titles)
        self.assertLess(titles.index('One-time Milestone'), titles.index('Recurring Practice'))

    def test_add_item_requires_deadline(self):
        response = self.client.post(
            f'/curriculums/{self.curriculum.id}/items',
            data={
                'title': 'No Deadline Task',
                'item_kind': 'daily',
                'daily_target_minutes': '30',
            },
            follow_redirects=True,
        )
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Every task needs a deadline.', body)
        self.assertEqual(CurriculumItem.query.count(), 0)

    def test_dashboard_today_focus_renders_recurring_and_one_time(self):
        recurring = CurriculumItem(
            curriculum_id=self.curriculum.id,
            title='Daily Scales',
            item_kind=CurriculumItem.KIND_DAILY,
            completion_style=CurriculumItem.STYLE_TIME_THRESHOLD,
            daily_target_minutes=45,
            deadline=date(2026, 5, 1),
        )
        one_time = CurriculumItem(
            curriculum_id=self.curriculum.id,
            title='Register Company',
            item_kind=CurriculumItem.KIND_ONE_SHOT,
            completion_style=CurriculumItem.STYLE_PRESENCE,
            one_time_target_minutes=180,
            deadline=date(2026, 4, 30),
        )
        db.session.add_all([recurring, one_time])
        db.session.commit()
        response = self.client.get('/')
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Today Focus', body)
        self.assertIn('Daily Scales', body)
        self.assertIn('Register Company', body)

    def test_dashboard_today_focus_shows_completed_one_time(self):
        with patch('app.routes.dashboard.local_today_for_user', return_value=date(2026, 5, 2)):
            done_item = CurriculumItem(
                curriculum_id=self.curriculum.id,
                title='Underestimated Sprint',
                item_kind=CurriculumItem.KIND_ONE_SHOT,
                completion_style=CurriculumItem.STYLE_PRESENCE,
                one_time_target_minutes=60,
                deadline=date(2026, 5, 10),
            )
            db.session.add(done_item)
            db.session.flush()
            db.session.add(Session(
                curriculum_id=self.curriculum.id,
                item_id=done_item.id,
                duration_minutes=70,
                logged_at=date(2026, 5, 2),
                source='manual',
            ))
            db.session.commit()
            response = self.client.get('/')
            body = response.get_data(as_text=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn('Underestimated Sprint', body)
            self.assertIn('Target met', body)
            self.assertIn('(+10 min over)', body)

    def test_dashboard_today_focus_orders_open_before_completed_one_time(self):
        with patch('app.routes.dashboard.local_today_for_user', return_value=date(2026, 5, 2)):
            open_item = CurriculumItem(
                curriculum_id=self.curriculum.id,
                title='AAA Still Open',
                item_kind=CurriculumItem.KIND_ONE_SHOT,
                completion_style=CurriculumItem.STYLE_PRESENCE,
                one_time_target_minutes=120,
                deadline=date(2026, 5, 20),
            )
            done_item = CurriculumItem(
                curriculum_id=self.curriculum.id,
                title='ZZZ Already Done',
                item_kind=CurriculumItem.KIND_ONE_SHOT,
                completion_style=CurriculumItem.STYLE_PRESENCE,
                one_time_target_minutes=30,
                deadline=date(2026, 5, 8),
            )
            db.session.add_all([open_item, done_item])
            db.session.flush()
            db.session.add(Session(
                curriculum_id=self.curriculum.id,
                item_id=done_item.id,
                duration_minutes=45,
                logged_at=date(2026, 5, 2),
                source='manual',
            ))
            db.session.commit()
            response = self.client.get('/')
            body = response.get_data(as_text=True)
            self.assertEqual(response.status_code, 200)
            self.assertLess(body.index('AAA Still Open'), body.index('ZZZ Already Done'))

    def test_dashboard_today_focus_hides_completed_one_time_past_deadline(self):
        with patch('app.routes.dashboard.local_today_for_user', return_value=date(2026, 5, 2)):
            done_past_deadline = CurriculumItem(
                curriculum_id=self.curriculum.id,
                title='Old Win',
                item_kind=CurriculumItem.KIND_ONE_SHOT,
                completion_style=CurriculumItem.STYLE_PRESENCE,
                one_time_target_minutes=60,
                deadline=date(2026, 5, 1),
            )
            db.session.add(done_past_deadline)
            db.session.flush()
            db.session.add(Session(
                curriculum_id=self.curriculum.id,
                item_id=done_past_deadline.id,
                duration_minutes=70,
                logged_at=date(2026, 5, 1),
                source='manual',
            ))
            db.session.commit()

            response = self.client.get('/')
            body = response.get_data(as_text=True)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('Old Win', body)


if __name__ == '__main__':
    unittest.main()
