"""Phase 0 smoke test: the skeleton compiles and the facade wires every module.

Individual module behavior is covered by each module's own Phase 1 test suite.
"""

from boogie_sdk import BoogieConfig, BoogieSdk


def test_facade_exposes_every_module_without_error():
    sdk = BoogieSdk.init(BoogieConfig(values={}))

    assert sdk.config is not None
    assert sdk.crypto is not None
    assert sdk.secret is not None
    assert sdk.token is not None
    assert sdk.cert is not None
    assert sdk.http is not None
    assert sdk.db is not None
    assert sdk.cache is not None
    assert sdk.queue is not None
    assert sdk.object_storage is not None
    assert sdk.service_discovery is not None
    assert sdk.scheduler is not None
    assert sdk.deviceio.protocol_client() is not None
    assert sdk.deviceio.file_polling() is not None
    assert sdk.deviceio.flat_file_parser() is not None
    assert sdk.deviceio.report_generator() is not None
    assert sdk.deviceio.batch_tracker() is not None
    assert sdk.deviceio.shift_calendar() is not None
    assert sdk.deviceio.spc_analyzer() is not None
    assert sdk.logger is not None
    assert sdk.metrics is not None
    assert sdk.tracer is not None
    assert sdk.id_generator is not None
    assert sdk.feature_flag is not None
    assert sdk.rate_limiter is not None
    assert sdk.notification is not None
    assert sdk.health is not None
    assert sdk.audit is not None

    sdk.close()


def test_facade_caches_client_instances():
    sdk = BoogieSdk.init(BoogieConfig(values={}))
    assert sdk.crypto is sdk.crypto
    assert sdk.deviceio.spc_analyzer() is sdk.deviceio.spc_analyzer()
