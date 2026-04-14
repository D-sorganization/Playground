"""Tests for Project_GROOT.train.rl_finetune - DbC and placeholder guards."""

import pytest

pytest.importorskip("torch")

import src.Project_GROOT.train.rl_finetune as target_module
from src.Project_GROOT.train.rl_finetune import (
    SimplePPOTrainer,
    _validate_rl_config,
    create_rl_config_template,
)


def test_module_syntax_and_import():
    """Verify Project_GROOT.train.rl_finetune can be imported."""
    assert target_module is not None


def test_has_symbol_SimplePPOTrainer():
    """Verify SimplePPOTrainer exists in module."""
    assert hasattr(target_module, "SimplePPOTrainer")


def test_has_symbol_create_rl_config_template():
    """Verify create_rl_config_template exists in module."""
    assert hasattr(target_module, "create_rl_config_template")


def test_has_symbol_main():
    """Verify main exists in module."""
    assert hasattr(target_module, "main")


def test_create_rl_config_template_valid():
    """Template config should pass validation."""
    config = create_rl_config_template()
    _validate_rl_config(config)  # Should not raise


def test_validate_rl_config_valid():
    """Valid config passes without exception."""
    config = create_rl_config_template()
    _validate_rl_config(config)


def test_validate_rl_config_missing_env():
    """Config without 'env' section fails assertion."""
    config = {
        "train": {
            "num_steps": 1000,
            "learning_rate": 1e-3,
            "gamma": 0.99,
            "clip_param": 0.2,
        }
    }
    with pytest.raises(AssertionError, match="env"):
        _validate_rl_config(config)


def test_validate_rl_config_missing_train():
    """Config without 'train' section fails assertion."""
    config = {"env": {"num_envs": 4}}
    with pytest.raises(AssertionError, match="train"):
        _validate_rl_config(config)


def test_validate_rl_config_negative_num_envs():
    """Negative num_envs fails assertion."""
    config = create_rl_config_template()
    config["env"]["num_envs"] = -1
    with pytest.raises(AssertionError, match="num_envs"):
        _validate_rl_config(config)


def test_validate_rl_config_zero_learning_rate():
    """Zero learning rate fails assertion."""
    config = create_rl_config_template()
    config["train"]["learning_rate"] = 0.0
    with pytest.raises(AssertionError, match="learning_rate"):
        _validate_rl_config(config)


def test_validate_rl_config_gamma_out_of_range():
    """Gamma > 1.0 fails assertion."""
    config = create_rl_config_template()
    config["train"]["gamma"] = 1.5
    with pytest.raises(AssertionError, match="gamma"):
        _validate_rl_config(config)


def test_validate_rl_config_clip_param_out_of_range():
    """clip_param >= 1.0 fails assertion."""
    config = create_rl_config_template()
    config["train"]["clip_param"] = 1.0
    with pytest.raises(AssertionError, match="clip_param"):
        _validate_rl_config(config)


def test_train_raises_not_implemented(tmp_path):
    """SimplePPOTrainer.train() raises NotImplementedError (scaffold guard)."""
    config = create_rl_config_template()
    trainer = SimplePPOTrainer(
        config=config,
        env_config=config["env"],
        pretrained_policy="dummy.pth",
        output_dir=str(tmp_path),
        device="cpu",
    )
    with pytest.raises(NotImplementedError, match="not yet implemented"):
        trainer.train()
