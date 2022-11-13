from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

from lib.tests import Suite101BaseTestCase

class TestUserModels(Suite101BaseTestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('test@test.com', 'foobar')

    def tearDown(self):
        del self.user

    """ Test user manager model methods """
    def test_user(self):
        "Check that users can be created and can set their password"
        User = get_user_model()
        u = User.objects.create_user('test@example.com', 'testpw')
        self.assertTrue(u.has_usable_password())
        self.assertFalse(u.check_password('bad'))
        self.assertTrue(u.check_password('testpw'))

        # Check we can manually set an unusable password
        u.set_unusable_password()
        u.save()
        self.assertFalse(u.check_password('testpw'))
        self.assertFalse(u.has_usable_password())
        u.set_password('testpw')
        self.assertTrue(u.check_password('testpw'))
        u.set_password(None)
        self.assertFalse(u.has_usable_password())

        # Check authentication/permissions
        self.assertTrue(u.is_authenticated())
        self.assertFalse(u.is_staff)
        self.assertFalse(u.is_active)
        self.assertFalse(u.is_superuser)

        # Check API-based user creation with no password
        u2 = User.objects.create_user('test2@example.com')
        self.assertFalse(u2.has_usable_password())

    def test_superuser(self):
        "Check the creation and properties of a superuser"
        User = get_user_model()
        super = User.objects.create_superuser('super@example.com', 'super')
        self.assertTrue(super.is_superuser)
        self.assertTrue(super.is_active)
        self.assertTrue(super.is_staff)

    """ Test User model methods """
    def test_get_full_name(self):
        self.user.first_name = 'Tester'
        self.user.last_name = 'Testerson'
        self.user.save()
        self.assertEqual(self.user.get_full_name(), 'Tester Testerson')

    def test_get_full_name_strip(self):
        self.user.first_name = 'Tester    '
        self.user.last_name = 'Testerson       '
        self.user.save()
        self.assertEqual(self.user.get_full_name(), 'Tester Testerson')

    def test_activation_key(self):
        """ ensure that the activation key is created and conforms to an SHA1 hash """
        import re
        SHA1_RE = re.compile('^[a-f0-9]{40}$')
        self.user.create_activation_key()
        self.assertTrue(SHA1_RE.search(self.user.activation_key))

    def test_activate_user(self):
        User = get_user_model()
        self.assertFalse(self.user.is_active)
        self.user.activate_user()
        user = User.objects.get(pk=self.user.pk)
        self.assertTrue(user.is_active)
