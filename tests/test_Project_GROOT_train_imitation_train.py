"""Tests for Project_GROOT.train.imitation_train - DbC contracts and helpers."""

import pytest

pytest.importorskip("torch")

import src.Project_GROOT.train.imitation_train as target_module
from src.Project_GROOT.train.imitation_train import (
    _build_imitation_parser,
    _load_and_override_config,
    _validate_imitation_config,
)


def _valid_config() -> dict:
    """Return a minimal valid imitation config."""
    return {
        "data": {"sequence_length": 90},
        "train": {
            "batch_size": 64,
            "learning_rate": 1e-3,
            "num_epochs": 10,
            "num_workers": 0,
        },
        "model": {"hidden_dims": [128, 64]},
    }


def test_module_syntax_and_import():
    """Verify Project_GROOT.train.imitation_train can be imported."""
    assert target_module is not None


def test_has_symbol_SwingDemonstrationDataset():
    """Verify SwingDemonstrationDataset exists in module."""
    assert hasattr(target_module, "SwingDemonstrationDataset")


def test_has_symbol_PolicyNetwork():
    """Verify PolicyNetwork exists in module."""
    assert hasattr(target_module, "PolicyNetwork")


def test_has_symbol_ImitationTrainer():
    """Verify ImitationTrainer exists in module."""
    assert hasattr(target_module, "ImitationTrainer")


def test_has_symbol_main():
    """Verify main exists in module."""
    assert hasattr(target_module, "main")


# --- _validate_imitation_config tests ---


def test_validate_config_valid():
    """Valid config passes without exception."""
    _validate_imitation_config(_valid_config())


def test_validate_config_missing_data_section():
    """Config without 'data' section fails assertion."""
    config = _valid_config()
    del config["data"]
    with pytest.raises(AssertionError, match="'data'"):
        _validate_imitation_config(config)


def test_validate_config_missing_train_section():
    """Config without 'train' section fails assertion."""
    config = _valid_config()
    del config["train"]
    with pytest.raises(AssertionError, match="'train'"):
        _validate_imitation_config(config)


def test_validate_config_missing_model_section():
    """Config without 'model' section fails assertion."""
    config = _valid_config()
    del config["model"]
    with pytest.raises(AssertionError, match="'model'"):
        _validate_imitation_config(config)


def test_validate_config_negative_sequence_length():
    """Negative sequence_length fails assertion."""
    config = _valid_config()
    config["data"]["sequence_length"] = -5
    with pytest.raises(AssertionError, match="sequence_length"):
        _validate_imitation_config(config)


def test_validate_config_zero_batch_size():
    """Zero batch_size fails assertion."""
    config = _valid_config()
    config["train"]["batch_size"] = 0
    with pytest.raises(AssertionError, match="batch_size"):
        _validate_imitation_config(config)


def test_validate_config_zero_learning_rate():
    """Zero learning_rate fails assertion."""
    config = _valid_config()
    config["train"]["learning_rate"] = 0.0
    with pytest.raises(AssertionError, match="learning_rate"):
        _validate_imitation_config(config)


def test_validate_config_empty_hidden_dims():
    """Empty hidden_dims list fails assertion."""
    config = _valid_config()
    config["model"]["hidden_dims"] = []
    with pytest.raises(AssertionError, match="hidden_dims"):
        _validate_imitation_config(config)


def test_validate_config_negative_hidden_dim():
    """Negative hidden dimension fails assertion."""
    config = _valid_config()
    config["model"]["hidden_dims"] = [128, -64]
    with pytest.raises(AssertionError, match="hidden_dims"):
        _validate_imitation_config(config)


# --- _build_imitation_parser tests ---


def test_build_imitation_parser_returns_parser():
    """_build_imitation_parser returns a working ArgumentParser."""
    import argparse

    parser = _build_imitation_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_build_imitation_parser_required_args():
    """Parsing without required args should fail."""
    with pytest.raises(SystemExit):
        _build_imitation_parser().parse_args([])


def test_build_imitation_parser_defaults():
    """Default seed and device are set."""
    args = _build_imitation_parser().parse_args(
        [
            "--config",
            "c.yaml",
            "--demo-dir",
            ".",
            "--output-dir",
            ".",
        ]
    )
    assert args.seed == 42
    assert args.resume is None


# --- _load_and_override_config tests ---


def test_load_and_override_config_applies_overrides(tmp_path):
    """CLI overrides replace config values."""
    import argparse

    import yaml

    config_data = _valid_config()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config_data))

    args = argparse.Namespace(
        config=str(config_path),
        output_dir=str(tmp_path),
        num_epochs=999,
        batch_size=None,
    )
    result = _load_and_override_config(args)
    assert result["train"]["num_epochs"] == 999


def test_load_and_override_config_saves_yaml(tmp_path):
    """_load_and_override_config saves config.yaml to output_dir."""
    import argparse

    import yaml

    config_data = _valid_config()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config_data))

    args = argparse.Namespace(
        config=str(config_path),
        output_dir=str(tmp_path / "output"),
        num_epochs=None,
        batch_size=None,
    )
    _load_and_override_config(args)
    assert (tmp_path / "output" / "config.yaml").exists()


# --- PolicyNetwork forward tests ---


def test_policy_network_forward():
    """PolicyNetwork forward pass produces correct output shape."""
    import torch

    from src.Project_GROOT.train.imitation_train import PolicyNetwork

    net = PolicyNetwork(state_dim=10, action_dim=5, hidden_dims=[32, 16])
    x = torch.randn(4, 10)
    out = net(x)
    assert out.shape == (4, 5)
