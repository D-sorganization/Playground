import logging
from typing import Any

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Imitation Learning Training Script for Project GROOT

Trains a policy to imitate retargeted golf swing demonstrations using
behavioral cloning.

Usage:
    python train/imitation_train.py --config train/configs/imitation_config.yaml \
        --demo-dir data/retargeted_demos --output-dir train/outputs/imitation_policy
"""

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import yaml
from torch.utils.data import DataLoader, Dataset
from torch.utils.tensorboard import SummaryWriter

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(x, **kwargs) -> Any:
        return x


class SwingDemonstrationDataset(Dataset):
    """Dataset of retargeted golf swing demonstrations."""

    def __init__(self, demo_dir: str, sequence_length: int = 90):
        """
        Args:
            demo_dir: Directory with retargeted .npz demo files
            sequence_length: Length of sequences to return
        """
        self.demo_dir = Path(demo_dir)
        self.sequence_length = sequence_length

        # Load all demonstrations
        self.demos = []
        self.demo_files = sorted(self.demo_dir.glob("*.npz"))

        for demo_file in self.demo_files:
            data = np.load(demo_file)
            self.demos.append(
                {
                    "q": data["q"],  # (T, num_dofs)
                    "qdot": data["qdot"],  # (T, num_dofs)
                    "ee_pos": data["ee_pos"],  # (T, 3)
                    "timestamps": data["timestamps"],  # (T,)
                }
            )

        logger.info(f"Loaded {len(self.demos)} demonstrations")

    def __len__(self) -> int:
        return len(self.demos)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        """Return a demonstration sequence."""
        demo = self.demos[idx]

        # Extract trajectory
        q = demo["q"]  # (T, num_dofs)
        qdot = demo["qdot"]
        ee_pos = demo["ee_pos"]

        T = len(q)

        # Pad or truncate to sequence_length
        if T < self.sequence_length:
            # Pad
            pad_len = self.sequence_length - T
            q = np.pad(q, ((0, pad_len), (0, 0)), mode="edge")
            qdot = np.pad(qdot, ((0, pad_len), (0, 0)), mode="edge")
            ee_pos = np.pad(ee_pos, ((0, pad_len), (0, 0)), mode="edge")
        else:
            # Truncate
            q = q[: self.sequence_length]
            qdot = qdot[: self.sequence_length]
            ee_pos = ee_pos[: self.sequence_length]

        # Compute normalized time steps
        time_steps = np.linspace(0, 1, self.sequence_length)

        # State: q + qdot + time
        state = np.concatenate(
            [q, qdot, time_steps[:, None]], axis=1
        )  # (T, num_dofs*2 + 1)

        # Action: q (position control)
        action = q

        return {
            "state": torch.FloatTensor(state),
            "action": torch.FloatTensor(action),
            "ee_pos": torch.FloatTensor(ee_pos),
        }


class PolicyNetwork(nn.Module):
    """Policy network for behavioral cloning."""

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_dims: list[int] | None = None,
    ):
        if hidden_dims is None:
            hidden_dims = [256, 256, 128]
        super().__init__()

        layers = []
        prev_dim = state_dim

        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.LayerNorm(hidden_dim))
            prev_dim = hidden_dim

        # Output layer
        layers.append(nn.Linear(prev_dim, action_dim))

        self.network = nn.Sequential(*layers)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """Forward pass."""
        return self.network(state)


class ImitationTrainer:
    """Trainer for imitation learning."""

    def __init__(
        self,
        config: dict,
        demo_dir: str,
        output_dir: str,
        device: str = "cuda",
    ):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.device = device

        # Create dataset
        self.dataset = SwingDemonstrationDataset(
            demo_dir=demo_dir,
            sequence_length=config["data"]["sequence_length"],
        )

        # Create dataloader
        self.dataloader = DataLoader(
            self.dataset,
            batch_size=config["train"]["batch_size"],
            shuffle=True,
            num_workers=config["train"].get("num_workers", 4),
        )

        # Get dimensions from first sample
        sample = self.dataset[0]
        state_dim = sample["state"].shape[1]
        action_dim = sample["action"].shape[1]

        logger.info(f"State dim: {state_dim}, Action dim: {action_dim}")

        # Create policy network
        self.policy = PolicyNetwork(
            state_dim=state_dim,
            action_dim=action_dim,
            hidden_dims=config["model"]["hidden_dims"],
        ).to(device)

        # Optimizer
        self.optimizer = optim.Adam(
            self.policy.parameters(),
            lr=config["train"]["learning_rate"],
            weight_decay=config["train"].get("weight_decay", 1e-5),
        )

        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=config["train"]["num_epochs"],
        )

        # Loss function
        self.criterion = nn.MSELoss()

        # Tensorboard
        self.writer = SummaryWriter(self.output_dir / "logs")

        # Tracking
        self.epoch = 0
        self.best_loss = float("inf")

    def train_epoch(self) -> dict:
        """Train for one epoch."""
        self.policy.train()

        epoch_losses = []

        for batch in tqdm(self.dataloader, desc=f"Epoch {self.epoch}"):
            state = batch["state"].to(self.device)  # (B, T, state_dim)
            action = batch["action"].to(self.device)  # (B, T, action_dim)

            # Flatten time dimension
            B, T, _ = state.shape
            state_flat = state.view(B * T, -1)
            action_flat = action.view(B * T, -1)

            # Forward pass
            pred_action = self.policy(state_flat)

            # Compute loss
            loss = self.criterion(pred_action, action_flat)

            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()

            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(
                self.policy.parameters(),
                self.config["train"].get("grad_clip", 1.0),
            )

            self.optimizer.step()

            epoch_losses.append(loss.item())

        # Average loss
        avg_loss = np.mean(epoch_losses)

        # Learning rate step
        self.scheduler.step()

        return {"loss": avg_loss, "lr": self.scheduler.get_last_lr()[0]}

    def save_checkpoint(self, is_best: bool = False) -> None:
        """Save model checkpoint."""
        checkpoint = {
            "epoch": self.epoch,
            "model_state_dict": self.policy.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scheduler_state_dict": self.scheduler.state_dict(),
            "config": self.config,
        }

        # Save latest
        checkpoint_path = self.output_dir / "checkpoints" / "latest.pth"
        checkpoint_path.parent.mkdir(exist_ok=True)
        torch.save(checkpoint, checkpoint_path)

        # Save epoch checkpoint
        epoch_path = self.output_dir / "checkpoints" / f"epoch_{self.epoch:04d}.pth"
        torch.save(checkpoint, epoch_path)

        # Save best
        if is_best:
            best_path = self.output_dir / "checkpoints" / "best.pth"
            torch.save(checkpoint, best_path)
            logger.info(f"  ✓ Saved best model (epoch {self.epoch})")

    def train(self) -> None:
        """Main training loop."""
        num_epochs = self.config["train"]["num_epochs"]

        logger.info(f"\nStarting training for {num_epochs} epochs")
        logger.info(f"Output directory: {self.output_dir}")

        for epoch in range(num_epochs):
            self.epoch = epoch

            # Train epoch
            metrics = self.train_epoch()

            # Log metrics
            self.writer.add_scalar("train/loss", metrics["loss"], epoch)
            self.writer.add_scalar("train/lr", metrics["lr"], epoch)

            logger.info(
                "Epoch %d/%d: loss=%.6f, lr=%.6f",
                epoch,
                num_epochs,
                metrics["loss"],
                metrics["lr"],
            )

            # Save checkpoint
            is_best = metrics["loss"] < self.best_loss
            if is_best:
                self.best_loss = metrics["loss"]

            if epoch % self.config["train"].get("save_freq", 50) == 0 or is_best:
                self.save_checkpoint(is_best=is_best)

        logger.info("\n✓ Training complete!")
        logger.info(f"  Best loss: {self.best_loss:.6f}")
        logger.info(f"  Checkpoints saved to: {self.output_dir / 'checkpoints'}")

        self.writer.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train imitation learning policy")

    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Training configuration YAML file",
    )
    parser.add_argument(
        "--demo-dir",
        type=str,
        required=True,
        help="Directory with retargeted demonstrations",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Output directory for checkpoints and logs",
    )
    parser.add_argument(
        "--num-epochs",
        type=int,
        help="Number of training epochs (overrides config)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Batch size (overrides config)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Device (cuda/cpu)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        help="Resume from checkpoint",
    )

    args = parser.parse_args()

    # Set random seed
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # Load config
    with open(args.config) as f:
        config = yaml.safe_load(f)

    # Override config from command line
    if args.num_epochs:
        config["train"]["num_epochs"] = args.num_epochs
    if args.batch_size:
        config["train"]["batch_size"] = args.batch_size

    # Save config to output dir
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)

    # Create trainer
    trainer = ImitationTrainer(
        config=config,
        demo_dir=args.demo_dir,
        output_dir=args.output_dir,
        device=args.device,
    )

    # Resume if specified
    if args.resume:
        checkpoint = torch.load(args.resume)
        trainer.policy.load_state_dict(checkpoint["model_state_dict"])
        trainer.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        trainer.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
        trainer.epoch = checkpoint["epoch"] + 1
        logger.info(f"Resumed from epoch {trainer.epoch}")

    # Train
    trainer.train()


if __name__ == "__main__":
    main()
