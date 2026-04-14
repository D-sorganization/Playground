"""Tests for Project_GROOT.train.imitation_train - behavioral and DbC tests.

Issue #274: Replace import/hasattr smoke tests with real behavioral tests for
training and retargeting modules.
"""

import argparse

import numpy as np
import pytest

torch = pytest.importorskip("torch", reason="torch not available")

from src.Project_GROOT.train.imitation_train import (  # noqa: E402
    PolicyNetwork,
    SwingDemonstrationDataset,
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


def _write_demo_npz(path, T: int = 20, num_dofs: int = 5):
    """Write a minimal demo .npz file for testing."""
    rng = np.random.default_rng(0)
    np.savez(
        path,
        q=rng.standard_normal((T, num_dofs)).astype(np.float32),
        qdot=rng.standard_normal((T, num_dofs)).astype(np.float32),
        ee_pos=rng.standard_normal((T, 3)).astype(np.float32),
        timestamps=np.linspace(0.0, 1.0, T).astype(np.float32),
    )


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


# --- _build_imitation_parser behavioral tests ---


def test_build_imitation_parser_returns_parser():
    """_build_imitation_parser returns a working ArgumentParser."""
    parser = _build_imitation_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_build_imitation_parser_required_args():
    """Parsing without required args should fail with SystemExit."""
    with pytest.raises(SystemExit):
        _build_imitation_parser().parse_args([])


def test_build_imitation_parser_defaults():
    """Default seed is 42 and resume defaults to None."""
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


# --- _load_and_override_config behavioral tests ---


def test_load_and_override_config_applies_overrides(tmp_path):
    """CLI overrides replace config values."""
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


# --- PolicyNetwork behavioral tests (issue #274) ---


def test_policy_network_forward():
    """PolicyNetwork forward pass produces correct output shape."""
    net = PolicyNetwork(state_dim=10, action_dim=5, hidden_dims=[32, 16])
    x = torch.randn(4, 10)
    out = net(x)
    assert out.shape == (4, 5)


def test_policy_network_forward_batch_independence():
    """PolicyNetwork output shape is consistent across batch sizes."""
    net = PolicyNetwork(state_dim=8, action_dim=3, hidden_dims=[16])
    for batch_size in (1, 4, 16):
        out = net(torch.randn(batch_size, 8))
        assert out.shape == (batch_size, 3)


def test_policy_network_default_hidden_dims():
    """PolicyNetwork uses default hidden_dims=[256,256,128] when not supplied."""
    net = PolicyNetwork(state_dim=6, action_dim=4)
    out = net(torch.randn(2, 6))
    assert out.shape == (2, 4)


def test_policy_network_output_finite():
    """PolicyNetwork forward pass outputs finite values for normal input."""
    net = PolicyNetwork(state_dim=5, action_dim=3, hidden_dims=[16])
    out = net(torch.randn(8, 5))
    assert torch.isfinite(out).all(), "PolicyNetwork output contains non-finite values"


# --- SwingDemonstrationDataset behavioral tests (issue #274) ---


def test_dataset_getitem_returns_tensors(tmp_path):
    """SwingDemonstrationDataset.__getitem__ returns torch.Tensor values."""
    _write_demo_npz(tmp_path / "demo_0.npz", T=30, num_dofs=5)
    ds = SwingDemonstrationDataset(str(tmp_path), sequence_length=20)
    sample = ds[0]
    assert isinstance(sample["state"], torch.Tensor)
    assert isinstance(sample["action"], torch.Tensor)
    assert isinstance(sample["ee_pos"], torch.Tensor)


def test_dataset_getitem_shape_truncate(tmp_path):
    """Longer demo is truncated to sequence_length along the time axis."""
    num_dofs = 4
    seq_len = 10
    _write_demo_npz(tmp_path / "demo_0.npz", T=30, num_dofs=num_dofs)
    ds = SwingDemonstrationDataset(str(tmp_path), sequence_length=seq_len)
    sample = ds[0]
    # state = [q, qdot, time] concatenated along dim=1
    assert sample["state"].shape == (seq_len, num_dofs * 2 + 1)
    assert sample["action"].shape == (seq_len, num_dofs)
    assert sample["ee_pos"].shape == (seq_len, 3)


def test_dataset_getitem_shape_pad(tmp_path):
    """Shorter demo is padded with edge values to sequence_length."""
    num_dofs = 4
    seq_len = 20
    _write_demo_npz(tmp_path / "demo_0.npz", T=8, num_dofs=num_dofs)
    ds = SwingDemonstrationDataset(str(tmp_path), sequence_length=seq_len)
    sample = ds[0]
    assert sample["state"].shape == (seq_len, num_dofs * 2 + 1)
    assert sample["action"].shape == (seq_len, num_dofs)
    assert sample["ee_pos"].shape == (seq_len, 3)


def test_dataset_len(tmp_path):
    """SwingDemonstrationDataset.__len__ returns number of demo files."""
    for i in range(3):
        _write_demo_npz(tmp_path / f"demo_{i}.npz")
    ds = SwingDemonstrationDataset(str(tmp_path), sequence_length=10)
    assert len(ds) == 3


def test_dataset_empty_dir(tmp_path):
    """SwingDemonstrationDataset handles empty directory gracefully."""
    ds = SwingDemonstrationDataset(str(tmp_path), sequence_length=10)
    assert len(ds) == 0
