import os

import pytest
from django import setup
from django.db.models import ExpressionWrapper, F, IntegerField
from hashids import Hashids

from django_hashids.exceptions import ConfigError

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
setup()

pytestmark = pytest.mark.django_db


def test_can_get_hashids():
    from django.conf import settings
    from tests.test_app.models import TestModel

    instance = TestModel.objects.create()
    hashid = instance.hashid
    hashids_instance = Hashids(salt=settings.DJANGO_HASHIDS_SALT)
    assert hashids_instance.decode(hashid)[0] == instance.pk


def test_can_get_field_from_model():
    from tests.test_app.models import TestModel

    TestModel.hashid


def test_can_use_per_field_config():
    from tests.test_app.models import TestModelWithDifferentConfig

    instance = TestModelWithDifferentConfig.objects.create()
    hashid = instance.hashid
    hashids_instance = Hashids(salt="AAA", min_length=5, alphabet="OPQRST1234567890")
    assert hashids_instance.decode(hashid)[0] == instance.pk


def test_can_use_per_field_instance():
    from tests.test_app.models import TestModelWithOwnInstance, this_hashids_instance

    instance = TestModelWithOwnInstance.objects.create()
    assert this_hashids_instance.decode(instance.hashid)[0] == instance.pk


def test_throws_when_setting_both_instance_and_config():
    from django.db.models import Model
    from tests.test_app.models import this_hashids_instance
    from django_hashids import HashidsField

    with pytest.raises(ConfigError):

        class Foo(Model):
            class Meta:
                app_label = "tests.test_app"

            hash_id = HashidsField(
                salt="Anotherone", hashids_instance=this_hashids_instance
            )


def test_updates_when_changing_real_column_value():
    from django.conf import settings
    from tests.test_app.models import TestModel

    instance = TestModel.objects.create()
    instance.id = 3
    # works before saving
    hashids_instance = Hashids(salt=settings.DJANGO_HASHIDS_SALT)
    assert hashids_instance.decode(instance.hashid)[0] == 3
    # works after saving
    instance.save()
    hashids_instance = Hashids(salt=settings.DJANGO_HASHIDS_SALT)
    assert hashids_instance.decode(instance.hashid)[0] == 3


def test_throws_trying_to_modify():
    from tests.test_app.models import TestModel

    instance = TestModel.objects.create()
    with pytest.raises(AttributeError):
        instance.hashid = "FOO"


def test_can_use_exact_lookup():
    from tests.test_app.models import TestModel

    instance = TestModel.objects.create()
    got_instance = TestModel.objects.filter(hashid=instance.hashid).first()
    assert instance == got_instance
    # assert id field still works
    got_instance = TestModel.objects.filter(id=instance.id).first()
    assert instance == got_instance


def test_can_use_in_lookup():
    from tests.test_app.models import TestModel

    instance = TestModel.objects.create()
    instance2 = TestModel.objects.create()
    hashids = [instance.hashid, instance2.hashid]
    qs = TestModel.objects.filter(hashid__in=hashids)
    assert set([instance, instance2]) == set(qs)


def test_can_use_lt_gt_lte_gte_lookup():
    from tests.test_app.models import TestModel

    instance = TestModel.objects.create()
    instance2 = TestModel.objects.create()
    qs = TestModel.objects.filter(hashid__lt=instance2.hashid)
    assert set([instance]) == set(qs)
    qs = TestModel.objects.filter(hashid__lte=instance2.hashid)
    assert set([instance, instance2]) == set(qs)
    qs = TestModel.objects.filter(hashid__gt=instance.hashid)
    assert set([instance2]) == set(qs)
    qs = TestModel.objects.filter(hashid__gte=instance.hashid)
    assert set([instance, instance2]) == set(qs)


def test_can_get_values():
    from tests.test_app.models import TestModel

    instance = TestModel.objects.create()
    instance2 = TestModel.objects.create()

    hashids = TestModel.objects.values("hashid")
    assert set([instance, instance2]) == set(
        TestModel.objects.filter(hashid__in=hashids)
    )
    hashids = list(TestModel.objects.values_list("hashid", flat=True))
    assert set([instance, instance2]) == set(
        TestModel.objects.filter(hashid__in=hashids)
    )
    # assert id field still works
    ids = list(TestModel.objects.values_list("id", flat=True))
    assert set([instance, instance2]) == set(TestModel.objects.filter(id__in=ids))


def test_can_select_as_integer():
    from tests.test_app.models import TestModel

    instance = TestModel.objects.create()
    instance2 = TestModel.objects.create()

    integer_ids = list(
        TestModel.objects.annotate(
            hid=ExpressionWrapper(F("hashid"), output_field=IntegerField())
        ).values_list("hid", flat=True)
    )
    assert set([instance.id, instance2.id]) == set(integer_ids)