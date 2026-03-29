import click
from app import db


def register_commands(app):
    @app.cli.command('seed')
    def seed():
        """Seed the database with Anthropic Interview Prep curriculum."""
        from app.models import Curriculum, CurriculumItem, Settings

        if Curriculum.query.count() > 0:
            click.echo('Database already seeded. Skipping.')
            return

        if not Settings.query.first():
            db.session.add(Settings())

        c = Curriculum(
            name='Anthropic Interview Prep',
            description='Structured preparation to make failure impossible. '
                        'Every hour logged is an hour closer to the goal.',
            mastery_hours=1000.0,
            color='#6366f1'
        )
        db.session.add(c)
        db.session.flush()

        from datetime import date, timedelta
        today = date.today()

        items = [
            ('Read "Attention Is All You Need"',
             'The original transformer paper. Understand every component.',
             today + timedelta(days=7), 10.0),
            ('Read "Constitutional AI" (Anthropic)',
             'Core alignment paper. Understand RLHF + CAI approach.',
             today + timedelta(days=10), 8.0),
            ('Read "Scaling Laws for Neural Language Models"',
             'Chinchilla scaling laws — fundamental to understanding LLM training.',
             today + timedelta(days=14), 6.0),
            ('Complete 50 LeetCode medium problems',
             'Focus on arrays, graphs, dynamic programming, trees.',
             today + timedelta(days=30), 50.0),
            ('Do 5 mock system design interviews',
             'Design Twitter, YouTube, distributed rate limiter, etc.',
             today + timedelta(days=21), 15.0),
            ('Build a toy transformer from scratch',
             'Implement attention, positional encoding, training loop in PyTorch.',
             today + timedelta(days=45), 20.0),
            ('Prepare 10 behavioral stories (STAR format)',
             'Impact, collaboration, failure, learning, leadership examples.',
             today + timedelta(days=14), 5.0),
            ('Study RLHF + reward modeling fundamentals',
             'PPO, reward models, preference data, InstructGPT paper.',
             today + timedelta(days=20), 10.0),
        ]

        for i, (title, desc, deadline, hours) in enumerate(items):
            db.session.add(CurriculumItem(
                curriculum_id=c.id,
                title=title,
                description=desc,
                deadline=deadline,
                hours_target=hours,
                sort_order=i
            ))

        db.session.commit()
        click.echo('✓ Seeded "Anthropic Interview Prep" with 8 items.')
        click.echo('  Run: .venv/bin/python run.py')
