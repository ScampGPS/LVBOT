"""Unit tests for user onboarding helpers in UserManager."""
from tracking import t

from types import SimpleNamespace

from users.manager import REQUIRED_PROFILE_FIELDS, UserManager


def _create_manager(tmp_path):
    t('tests.unit.test_user_manager._create_manager')
    return UserManager(str(tmp_path / 'users.json'))


def test_ensure_user_profile_creates_new_entry(tmp_path):
    t('tests.unit.test_user_manager.test_ensure_user_profile_creates_new_entry')
    manager = _create_manager(tmp_path)
    telegram_user = SimpleNamespace(
        id=123,
        first_name=' Jane ',
        last_name='Doe',
        username='jdoe',
        language_code='en',
    )

    profile, created = manager.ensure_user_profile(telegram_user)

    assert created is True
    assert profile['user_id'] == 123
    assert profile['first_name'] == 'Jane'
    assert profile['last_name'] == 'Doe'
    assert profile['language'] == 'en'
    # Persisted copy should match
    stored = manager.get_user(123)
    assert stored is not None
    assert stored['username'] == 'jdoe'


def test_ensure_user_profile_returns_existing_entry(tmp_path):
    t('tests.unit.test_user_manager.test_ensure_user_profile_returns_existing_entry')
    manager = _create_manager(tmp_path)
    manager.save_user(
        {
            'user_id': 5,
            'first_name': 'Existing',
            'last_name': 'User',
            'email': 'existing@example.com',
            'phone': '12345678',
            'language': 'es',
        }
    )

    telegram_user = SimpleNamespace(id=5, first_name='New', last_name='Name', language_code='en')
    profile, created = manager.ensure_user_profile(telegram_user)

    assert created is False
    # Existing profile should remain unchanged
    assert profile['first_name'] == 'Existing'
    assert profile['language'] == 'es'


def test_get_missing_profile_fields(tmp_path):
    t('tests.unit.test_user_manager.test_get_missing_profile_fields')
    manager = _create_manager(tmp_path)
    profile = {
        'first_name': 'Saul',
        'last_name': '',
        'email': 'user@example.com',
        'phone': '',
    }

    missing = manager.get_missing_profile_fields(profile)
    assert missing == ['last_name', 'phone']

    missing_when_none = manager.get_missing_profile_fields(None)
    assert missing_when_none == list(REQUIRED_PROFILE_FIELDS)
