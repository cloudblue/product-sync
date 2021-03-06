#  Copyright © 2021 CloudBlue. All rights reserved.

import os
import tempfile
import json
from json.decoder import JSONDecodeError

import pytest
import toml
from click import ClickException
from cookiecutter.config import DEFAULT_CONFIG
from cookiecutter.exceptions import OutputDirExistsException
from cookiecutter.utils import work_in
from pkg_resources import EntryPoint

from connect.cli.core.config import Config
from connect.cli.plugins.project.extension_helpers import (
    bootstrap_extension_project,
    validate_extension_project,
)
from connect.cli.plugins.project import utils


def _cookiecutter_result(local_path):
    os.makedirs(f'{local_path}/project_dir/connect_ext')
    open(f'{local_path}/project_dir/connect_ext/README.md', 'w').write('# Extension')


@pytest.mark.parametrize('exists_cookiecutter_dir', (True, False))
@pytest.mark.parametrize('is_bundle', (True, False))
def test_bootstrap_extension_project(
    fs,
    mocker,
    capsys,
    exists_cookiecutter_dir,
    is_bundle,
    config_mocker,
):
    config = Config()
    config.load(config_dir='/tmp')
    mocked_cookiecutter = mocker.patch(
        'connect.cli.plugins.project.extension_helpers.cookiecutter',
        return_value='project_dir',
    )
    mocked_dialogus = mocker.patch(
        'connect.cli.plugins.project.utils.dialogus',
        return_value={
            'project_name': 'foo',
            'package_name': 'bar',
            'license': 'super one',
            'use_github_actions': 'y',
            'asset_processing': [],
            'asset_validation': [],
            'tierconfig': [],
            'product': [],
        },
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.open',
        mocker.mock_open(read_data='#Project'),
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.is_bundle',
        return_value=is_bundle,
    )
    extension_json = {
        'name': 'my super project',
        'capabilities': {
            'asset_purchase_request_processing': ['draft'],
        },
    }
    mocked_open = mocker.patch(
        'connect.cli.plugins.project.utils.open',
        mocker.mock_open(read_data=str(extension_json)),
    )
    mocked_open = mocker.patch(
        'connect.cli.plugins.project.utils.json.load',
        return_value=mocked_open.return_value,
    )
    mocked_open = mocker.patch(
        'connect.cli.plugins.project.utils.json.dump',
        return_value=mocked_open.return_value,
    )
    cookie_dir = f'{fs.root_path}/.cookiecutters'
    if exists_cookiecutter_dir:
        os.mkdir(cookie_dir)
    DEFAULT_CONFIG['cookiecutters_dir'] = cookie_dir

    output_dir = f'{fs.root_path}/projects'
    os.mkdir(output_dir)
    bootstrap_extension_project(config, output_dir)

    captured = capsys.readouterr()
    assert 'project_dir' in captured.out
    assert mocked_cookiecutter.call_count == 1
    assert mocked_dialogus.call_count == 6


def test_bootstrap_direxists_error(fs, mocker, config_mocker):
    config = Config()
    config.load(config_dir='/tmp')
    mocked_cookiecutter = mocker.patch(
        'connect.cli.plugins.project.extension_helpers.cookiecutter',
        side_effect=OutputDirExistsException('dir "project_dir" exists'),
    )
    mocked_dialogus = mocker.patch(
        'connect.cli.plugins.project.utils.dialogus',
        return_value={
            'project_name': 'foo',
            'package_name': 'bar',
            'asset_processing': [],
            'asset_validation': [],
            'tierconfig': [],
            'product': [],
        },
    )
    cookie_dir = f'{fs.root_path}/.cookiecutters'
    os.mkdir(cookie_dir)
    DEFAULT_CONFIG['cookiecutters_dir'] = cookie_dir

    output_dir = f'{fs.root_path}/projects'
    os.mkdir(output_dir)

    with pytest.raises(ClickException):
        bootstrap_extension_project(config, output_dir)
    assert mocked_cookiecutter.call_count == 1
    assert mocked_dialogus.call_count == 6


def test_bootstrap_show_empty_dialog(mocker):
    mocked_dialogus = mocker.patch(
        'connect.cli.plugins.project.utils.dialogus',
        return_value={},
    )
    with pytest.raises(ClickException):
        utils._show_dialog({}, 1, 5)

    assert mocked_dialogus.call_count == 1


def test_bootstrap_generate_capabilities():
    answers = {'asset': ['one', 'two']}
    cookiecutter_answers = utils._gen_cookie_capabilities(answers['asset'])

    assert cookiecutter_answers['one'] == 'y'
    assert cookiecutter_answers['two'] == 'y'


def test_validate_sync_project(mocker, capsys):
    project_dir = './tests/fixtures/extensions/basic_ext'

    class BasicExtension:
        def process_asset_purchase_request(self):
            pass

        def process_tier_config_setup_request(self):
            pass

        def execute_product_action(self):
            pass

        def process_product_custom_event(self):
            pass

    mocker.patch.object(
        EntryPoint,
        'load',
        return_value=BasicExtension,
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.pkg_resources.iter_entry_points',
        return_value=iter([
            EntryPoint('extension', 'connect.eaas.ext'),
        ]),
    )
    validate_extension_project(project_dir)

    captured = capsys.readouterr()
    assert 'successfully' in captured.out


def test_validate_async_project(mocker, capsys):
    project_dir = './tests/fixtures/extensions/basic_ext'

    class BasicExtension:
        async def process_asset_purchase_request(self):
            pass

        async def process_tier_config_setup_request(self):
            pass

        async def execute_product_action(self):
            pass

        async def process_product_custom_event(self):
            pass

    mocker.patch.object(
        EntryPoint,
        'load',
        return_value=BasicExtension,
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.pkg_resources.iter_entry_points',
        return_value=iter([
            EntryPoint('extension', 'connect.eaas.ext'),
        ]),
    )
    validate_extension_project(project_dir)

    captured = capsys.readouterr()
    assert 'successfully' in captured.out


def test_validate_wrong_project_dir():
    project_dir = './tests'
    with pytest.raises(ClickException) as error:
        validate_extension_project(project_dir)

    assert 'does not look like an extension project directory' in str(error.value)


def test_validate_wrong_pyproject_file():
    with tempfile.TemporaryDirectory() as tmp_project_dir:
        open(f'{tmp_project_dir}/pyproject.toml', 'w').write('foo')
        with pytest.raises(ClickException) as error:
            validate_extension_project(tmp_project_dir)

    assert 'The extension project descriptor file `pyproject.toml` is not valid.' in str(error.value)


def test_validate_wrong_plugin_declaration(mocked_extension_project_descriptor):
    pyproject_content = mocked_extension_project_descriptor
    pyproject_content['tool']['poetry']['plugins']['connect.eaas.ext'] = 'foo'
    with tempfile.TemporaryDirectory() as tmp_project_dir:
        toml.dump(pyproject_content, open(f'{tmp_project_dir}/pyproject.toml', 'w'))
        with pytest.raises(ClickException) as error:
            validate_extension_project(tmp_project_dir)

    assert 'plugins."connect.eaas.ext"] `pyproject.toml` section is not well configured' in str(error.value)


def test_validate_plugin_with_no_extension_key(mocked_extension_project_descriptor):
    pyproject_content = mocked_extension_project_descriptor
    pyproject_content['tool']['poetry']['plugins']['connect.eaas.ext'] = {'newkey': 'pkg.extension:BasicExtension'}
    with tempfile.TemporaryDirectory() as tmp_project_dir:
        toml.dump(pyproject_content, open(f'{tmp_project_dir}/pyproject.toml', 'w'))
        with pytest.raises(ClickException) as error:
            validate_extension_project(tmp_project_dir)

    assert 'plugins."connect.eaas.ext"] `pyproject.toml` section does not have "extension"' in str(error.value)


def test_validate_not_loaded():
    project_dir = './tests/fixtures/extensions/basic_ext'
    with pytest.raises(ClickException) as error:
        validate_extension_project(project_dir)

    assert 'The extension could not be loaded, Did you execute `poetry install`?' in str(error.value)


def test_validate_object_loaded_from_plugin_not_a_class(
    mocker,
):
    project_dir = './tests/fixtures/extensions/basic_ext'

    def _foo():
        pass

    mocked_load = mocker.patch.object(
        EntryPoint,
        'load',
        return_value=_foo,
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.pkg_resources.iter_entry_points',
        return_value=iter([
            EntryPoint('extension', 'connect.eaas.ext'),
        ]),
    )
    with pytest.raises(ClickException) as error:
        validate_extension_project(project_dir)

    assert f'The extension class {mocked_load.return_value} does not seem a class' in str(error.value)


def test_validate_extension_json_descriptor(
    mocker,
):
    project_dir = './tests/fixtures/extensions/basic_ext'

    class BasicExtension:
        pass

    mocker.patch.object(
        EntryPoint,
        'load',
        return_value=BasicExtension,
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.pkg_resources.iter_entry_points',
        return_value=iter([
            EntryPoint('extension', 'connect.eaas.ext'),
        ]),
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.json.load',
        side_effect=JSONDecodeError('error', '', 0),
    )
    with pytest.raises(ClickException) as error:
        validate_extension_project(project_dir)

    assert 'The extension descriptor file `extension.json` could not be loaded.' in str(error.value)


def test_validate_methods_not_match_capabilities(
    mocker,
):
    project_dir = './tests/fixtures/extensions/basic_ext'

    # On the extension project fixture there are 4 capabilities defined
    class BasicExtension:
        def process_asset_purchase_request(self):
            pass

    mocker.patch.object(
        EntryPoint,
        'load',
        return_value=BasicExtension,
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.pkg_resources.iter_entry_points',
        return_value=iter([
            EntryPoint('extension', 'connect.eaas.ext'),
        ]),
    )

    with pytest.raises(ClickException) as error:
        validate_extension_project(project_dir)

    assert 'There is some mismatch between capabilities' in str(error.value)


def test_validate_methods_mixed_sync_async(
    mocker,
):
    project_dir = './tests/fixtures/extensions/basic_ext'

    class TestExtension:
        def process_asset_purchase_request(self):
            pass

        def process_tier_config_setup_request(self):
            pass

        async def execute_product_action(self):
            pass

        async def process_product_custom_event(self):
            pass

    mocker.patch.object(
        EntryPoint,
        'load',
        return_value=TestExtension,
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.pkg_resources.iter_entry_points',
        return_value=iter([
            EntryPoint('extension', 'connect.eaas.ext'),
        ]),
    )

    with pytest.raises(ClickException) as error:
        validate_extension_project(project_dir)

    assert 'An Extension class can only have sync or async methods not a mix of both.' in str(error.value)


def test_validate_capabilities_with_wrong_status(
    mocker,
    mocked_extension_descriptor,
):
    project_dir = './tests/fixtures/extensions/basic_ext'

    class TestExtension:
        def process_asset_purchase_request(self):
            pass

    mocker.patch.object(
        EntryPoint,
        'load',
        return_value=TestExtension,
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.pkg_resources.iter_entry_points',
        return_value=iter([
            EntryPoint('extension', 'connect.eaas.ext'),
        ]),
    )
    mocked_extension_descriptor['capabilities']['asset_purchase_request_processing'] = ['foo']
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.json.load',
        return_value=mocked_extension_descriptor,
    )
    with pytest.raises(ClickException) as error:
        validate_extension_project(project_dir)

    assert 'Status `foo` on capability `asset_purchase_request_processing` is not allowed.' in str(error.value)


def test_validate_wrong_capability_without_status(
    mocker,
    mocked_extension_descriptor,
):
    project_dir = './tests/fixtures/extensions/basic_ext'

    class TestExtension:
        def process_asset_purchase_request(self):
            pass

    mocker.patch.object(
        EntryPoint,
        'load',
        return_value=TestExtension,
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.pkg_resources.iter_entry_points',
        return_value=iter([
            EntryPoint('extension', 'connect.eaas.ext'),
        ]),
    )
    mocked_extension_descriptor['capabilities']['asset_purchase_request_processing'] = []
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.json.load',
        return_value=mocked_extension_descriptor,
    )
    with pytest.raises(ClickException) as error:
        validate_extension_project(project_dir)

    assert 'Capability `asset_purchase_request_processing` must have at least one allowed status.' in str(error.value)


@pytest.mark.parametrize(
    'capability',
    (
        'product_action_execution',
        'product_custom_event_processing',
        'asset_purchase_request_processing',
    ),
)
def test_validate_product_capability_with_status(
    mocker,
    mocked_extension_descriptor,
    capability,
    capsys,
):
    project_dir = './tests/fixtures/extensions/basic_ext'

    class TestExtension:
        def process_asset_purchase_request(self):
            pass

        def process_tier_config_setup_request(self):
            pass

        def execute_product_action(self):
            pass

        def process_product_custom_event(self):
            pass

    mocker.patch.object(
        EntryPoint,
        'load',
        return_value=TestExtension,
    )
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.pkg_resources.iter_entry_points',
        return_value=iter([
            EntryPoint('extension', 'connect.eaas.ext'),
        ]),
    )
    mocked_extension_descriptor['capabilities'][capability] = ['approved']
    mocker.patch(
        'connect.cli.plugins.project.extension_helpers.json.load',
        return_value=mocked_extension_descriptor,
    )
    if capability == 'product_action_execution' or capability == 'product_custom_event_processing':
        with pytest.raises(ClickException) as error:
            validate_extension_project(project_dir)
        assert f'Capability `{capability}` must not have status.' in str(error.value)
    else:
        validate_extension_project(project_dir)
        captured = capsys.readouterr()
        assert 'successfully' in captured.out


@pytest.mark.parametrize(
    'package_name',
    ('good-one', 'wron@##)one'),
)
@pytest.mark.parametrize(
    'project_name',
    ('good-one', 'wron@##)one'),
)
def test_bootstrap_pre_gen_cookiecutter(project_name, package_name):
    answers = {'project_name': project_name, 'package_name': package_name}
    if project_name == 'wron@##)one' or package_name == 'wron@##)one':
        with pytest.raises(ClickException) as error:
            utils.pre_gen_cookiecutter_extension_hook(answers)
        assert 'slug is not a valid Python identifier' in str(error.value)


@pytest.mark.parametrize(
    ('answer', 'capability'),
    (
        ('subscription_process_capabilities_1of6', 'asset_purchase_request_processing'),
        ('subscription_process_capabilities_2of6', 'asset_change_request_processing'),
        ('subscription_process_capabilities_3of6', 'asset_suspend_request_processing'),
        ('subscription_process_capabilities_4of6', 'asset_resume_request_processing'),
        ('subscription_process_capabilities_5of6', 'asset_cancel_request_processing'),
        ('subscription_process_capabilities_6of6', 'asset_adjustment_request_processing'),
        ('subscription_validation_capabilities_1of2', 'asset_purchase_request_validation'),
        ('subscription_validation_capabilities_2of2', 'asset_change_request_validation'),
        ('tier_config_process_capabilities_1of2', 'tier_config_setup_request_processing'),
        ('tier_config_process_capabilities_2of2', 'tier_config_change_request_processing'),
        ('tier_config_validation_capabilities_1of2', 'tier_config_setup_request_validation'),
        ('tier_config_validation_capabilities_2of2', 'tier_config_change_request_validation'),
        ('product_capabilities_1of2', 'product_action_execution'),
        ('product_capabilities_2of2', 'product_custom_event_processing'),
    ),
)
def test_post_gen_cookiecutter_hook(mocker, answer, capability):
    mocker.patch(
        'connect.cli.plugins.project.utils.os.remove',
    )
    mocker.patch(
        'connect.cli.plugins.project.utils.shutil.rmtree',
    )
    answers = {
        'project_name': 'project',
        'package_name': 'package',
        'license': 'Other, not Open-source',
        'use_github_actions': 'n',
        answer: 'y',
    }
    extension_json = {
        'name': 'my super project',
        'capabilities': {},
    }
    with tempfile.TemporaryDirectory() as tmp_data:
        os.mkdir(f'{tmp_data}/project')
        os.mkdir(f'{tmp_data}/project/package')
        with open(f'{tmp_data}/project/package/extension.json', 'w') as fp:
            json.dump(extension_json, fp)
        with work_in(f'{tmp_data}'):
            utils.post_gen_cookiecutter_extension_hook(answers)

        with open(f'{tmp_data}/project/package/extension.json', 'r') as fp:
            data = json.load(fp)

        assert capability in data['capabilities'].keys()
        assert isinstance(data['capabilities'][capability], list)
        if answer == 'product_capabilities_1of2' or answer == 'product_capabilities_2of2':
            assert data['capabilities'][capability] == []
        else:
            assert data[
                'capabilities'
            ][capability] == ['draft', 'tiers_setup', 'pending', 'inquiring', 'approved', 'failed']
