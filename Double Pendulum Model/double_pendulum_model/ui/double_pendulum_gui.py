"""
Interactive driven double pendulum GUI for educational demonstrations.

The interface is intentionally simple: it accepts initial angles, adjustable
masses/lengths, and symbolic torque expressions, then renders a 2D pendulum on a
user-defined swing plane. Rendering uses Tkinter's canvas so it remains portable
and easy to embed in classroom laptops or web-streamed demos.
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from typing import Optional

from double_pendulum_model.physics.double_pendulum import (
    DEFAULT_PLANE_INCLINATION_DEG,
    DoublePendulumDynamics,
    DoublePendulumParameters,
    DoublePendulumState,
    compile_forcing_functions,
)

CANVAS_SIZE = 780
PIVOT_POINT = (CANVAS_SIZE // 2, CANVAS_SIZE // 5)
TIME_STEP = 0.01
SCALE_PIXELS_PER_METER = 320


@dataclass
class UserInputs:
    shoulder_angle_deg: float
    wrist_angle_deg: float
    shoulder_expression: str
    wrist_expression: str
    upper_length_m: float
    upper_mass_kg: float
    upper_com_ratio: float
    lower_length_m: float
    shaft_mass_kg: float
    clubhead_mass_kg: float
    shaft_com_ratio: float
    plane_inclination_deg: float


class DoublePendulumApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Driven Double Pendulum — Control Affine Model")
        self.canvas = tk.Canvas(root, width=CANVAS_SIZE, height=CANVAS_SIZE, bg="white")
        self.canvas.grid(row=0, column=0, rowspan=20)

        self.inputs = self._build_input_panel()

        self.state: Optional[DoublePendulumState] = None
        self.dynamics: Optional[DoublePendulumDynamics] = None
        self.time = 0.0
        self.running = False
        self._draw_plane_guides(DEFAULT_PLANE_INCLINATION_DEG)

    def _build_input_panel(self) -> UserInputs:
        panel = tk.Frame(self.root)
        panel.grid(row=0, column=1, sticky="n")

        entries = {}

        def labeled_row(label: str, default: str, row: int) -> tk.Entry:
            tk.Label(panel, text=label).grid(row=row, column=0, sticky="w")
            entry = tk.Entry(panel)
            entry.insert(0, default)
            entry.grid(row=row, column=1)
            entries[label] = entry
            return entry

        labeled_row("Shoulder angle (deg)", "-45", 0)
        labeled_row("Wrist angle (deg)", "-90", 1)
        labeled_row("Shoulder torque f(t)", "0.0", 2)
        labeled_row("Wrist torque f(t)", "0.0", 3)
        labeled_row("Upper length (m)", "0.75", 4)
        labeled_row("Upper mass (kg)", "7.5", 5)
        labeled_row("Upper COM ratio", "0.45", 6)
        labeled_row("Lower length (m)", "1.0", 7)
        labeled_row("Shaft mass (kg)", "0.35", 8)
        labeled_row("Clubhead mass (kg)", "0.20", 9)
        labeled_row("Shaft COM ratio", "0.43", 10)
        labeled_row("Plane incline (deg)", str(DEFAULT_PLANE_INCLINATION_DEG), 11)

        start_button = tk.Button(panel, text="Start", command=self.start)
        start_button.grid(row=12, column=0, pady=6)
        tk.Button(panel, text="Pause", command=self.pause).grid(row=12, column=1, pady=6)

        self.torque_label = tk.Label(panel, text="Torques: --")
        self.torque_label.grid(row=13, column=0, columnspan=2, pady=4)

        self.entries = entries
        return UserInputs(
            shoulder_angle_deg=-45.0,
            wrist_angle_deg=-90.0,
            shoulder_expression="0.0",
            wrist_expression="0.0",
            upper_length_m=0.75,
            upper_mass_kg=7.5,
            upper_com_ratio=0.45,
            lower_length_m=1.0,
            shaft_mass_kg=0.35,
            clubhead_mass_kg=0.20,
            shaft_com_ratio=0.43,
            plane_inclination_deg=DEFAULT_PLANE_INCLINATION_DEG,
        )

    def _read_inputs(self) -> UserInputs:
        def get_float(label: str) -> float:
            return float(self.entries[label].get())

        return UserInputs(
            shoulder_angle_deg=get_float("Shoulder angle (deg)"),
            wrist_angle_deg=get_float("Wrist angle (deg)"),
            shoulder_expression=self.entries["Shoulder torque f(t)"].get(),
            wrist_expression=self.entries["Wrist torque f(t)"].get(),
            upper_length_m=get_float("Upper length (m)"),
            upper_mass_kg=get_float("Upper mass (kg)"),
            upper_com_ratio=get_float("Upper COM ratio"),
            lower_length_m=get_float("Lower length (m)"),
            shaft_mass_kg=get_float("Shaft mass (kg)"),
            clubhead_mass_kg=get_float("Clubhead mass (kg)"),
            shaft_com_ratio=get_float("Shaft COM ratio"),
            plane_inclination_deg=get_float("Plane incline (deg)"),
        )

    def start(self) -> None:
        user_inputs = self._read_inputs()
        upper_inertia = (1.0 / 12.0) * user_inputs.upper_mass_kg * user_inputs.upper_length_m**2
        parameters = DoublePendulumParameters(
            upper_segment=DoublePendulumParameters.default().upper_segment.__class__(
                length_m=user_inputs.upper_length_m,
                mass_kg=user_inputs.upper_mass_kg,
                center_of_mass_ratio=user_inputs.upper_com_ratio,
                inertia_about_com=upper_inertia,
            ),
            lower_segment=DoublePendulumParameters.default().lower_segment.__class__(
                length_m=user_inputs.lower_length_m,
                shaft_mass_kg=user_inputs.shaft_mass_kg,
                clubhead_mass_kg=user_inputs.clubhead_mass_kg,
                shaft_com_ratio=user_inputs.shaft_com_ratio,
            ),
            plane_inclination_deg=user_inputs.plane_inclination_deg,
        )
        forcing = compile_forcing_functions(
            user_inputs.shoulder_expression, user_inputs.wrist_expression
        )
        self.dynamics = DoublePendulumDynamics(parameters=parameters, forcing_functions=forcing)
        self.state = DoublePendulumState(
            theta1=math.radians(user_inputs.shoulder_angle_deg),
            theta2=math.radians(user_inputs.wrist_angle_deg),
            omega1=0.0,
            omega2=0.0,
        )
        self.time = 0.0
        self.running = True
        self._draw_plane_guides(parameters.plane_inclination_deg)
        self._update()

    def pause(self) -> None:
        self.running = False

    def _draw_plane_guides(self, plane_deg: float) -> None:
        self.canvas.delete("all")
        plane_rad = math.radians(plane_deg)
        dx = math.sin(plane_rad) * CANVAS_SIZE
        dy = math.cos(plane_rad) * CANVAS_SIZE
        x0, y0 = PIVOT_POINT
        self.canvas.create_line(x0 - dx, y0 + dy, x0 + dx, y0 - dy, fill="#b0b0b0", dash=(6, 3))

    def _update(self) -> None:
        if not self.running or self.state is None or self.dynamics is None:
            return

        self.state = self.dynamics.step(self.time, self.state, TIME_STEP)
        self.time += TIME_STEP

        self._draw_pendulum()

        torques = self.dynamics.applied_torques(self.time, self.state)
        breakdown = self.dynamics.joint_torque_breakdown(self.state, torques)
        self.torque_label.config(
            text=(
                f"Applied (Nm): shoulder={torques[0]: .2f}, wrist={torques[1]: .2f}\n"
                f"Gravity: {breakdown.gravitational[0]: .2f}, {breakdown.gravitational[1]: .2f}"
            )
        )
        self.root.after(int(TIME_STEP * 1000), self._update)

    def _draw_pendulum(self) -> None:
        if self.state is None or self.dynamics is None:
            return

        upper = self.dynamics.parameters.upper_segment
        lower = self.dynamics.parameters.lower_segment
        pivot_x, pivot_y = PIVOT_POINT

        upper_dx = math.sin(self.state.theta1) * upper.length_m * SCALE_PIXELS_PER_METER
        upper_dy = math.cos(self.state.theta1) * upper.length_m * SCALE_PIXELS_PER_METER
        elbow_x = pivot_x + upper_dx
        elbow_y = pivot_y + upper_dy

        lower_dx = (
            math.sin(self.state.theta1 + self.state.theta2)
            * lower.length_m
            * SCALE_PIXELS_PER_METER
        )
        lower_dy = (
            math.cos(self.state.theta1 + self.state.theta2)
            * lower.length_m
            * SCALE_PIXELS_PER_METER
        )
        wrist_x = elbow_x + lower_dx
        wrist_y = elbow_y + lower_dy

        self.canvas.delete("pendulum")
        self.canvas.create_line(
            pivot_x, pivot_y, elbow_x, elbow_y, width=5, fill="#2c7bb6", tags="pendulum"
        )
        self.canvas.create_line(
            elbow_x, elbow_y, wrist_x, wrist_y, width=6, fill="#d7191c", tags="pendulum"
        )
        self.canvas.create_oval(
            wrist_x - 10,
            wrist_y - 10,
            wrist_x + 10,
            wrist_y + 10,
            fill="#d7191c",
            outline="",
            tags="pendulum",
        )


def run_app() -> None:
    root = tk.Tk()
    app = DoublePendulumApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_app()
