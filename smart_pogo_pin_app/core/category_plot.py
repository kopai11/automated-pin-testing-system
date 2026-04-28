import math
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from PySide6.QtWidgets import QWidget, QVBoxLayout


class CategoryPlotPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)

        self.fig = Figure(figsize=(10, 7), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)

        lay.addWidget(self.toolbar)
        lay.addWidget(self.canvas)

        # Three stacked plots: Current, Resistance, Force
        self.ax_cur = self.fig.add_subplot(3, 1, 1)
        self.ax_res = self.fig.add_subplot(3, 1, 2, sharex=self.ax_cur)
        self.ax_force = self.fig.add_subplot(3, 1, 3, sharex=self.ax_cur)

        self.x = []
        self.cur = []
        self.res = []
        self.force = []
        self.N = 0
        self.window_size = 10
        self.plot_color = 'blue'
        self.display_start_idx = 0

        self.cursor_cur = None
        self.cursor_res = None
        self.info = None

        self._cid = self.canvas.mpl_connect("motion_notify_event", self._on_move)

    def set_data(self, label_text, cur_vals, res_vals, force_vals=None, y_max=3000, window_size=10, color='blue',
                 cur_vals_other=None, res_vals_other=None, color_other='red', show_all_data=False, line_width=1.5):
        self._line_width = line_width
        self.ax_cur.clear()
        self.ax_res.clear()
        self.ax_force.clear()

        # TM values
        self.cur = list(cur_vals)
        self.res = list(res_vals)
        self.force = list(force_vals) if force_vals is not None else []
        
        # Other values
        self.cur_other = list(cur_vals_other) if cur_vals_other is not None else []
        self.res_other = list(res_vals_other) if res_vals_other is not None else []
        
        # if no force provided, pad zeros to match current/res length
        if not self.force and self.res:
            self.force = [0.0] * len(self.res)

        self.N = min(len(self.cur), len(self.res), len(self.force)) if self.force else min(len(self.cur), len(self.res))
        self.N_other = min(len(self.cur_other), len(self.res_other)) if self.cur_other and self.res_other else 0
        self.has_other = self.N_other > 0
        self.window_size = window_size
        self.plot_color = color
        self.plot_color_other = color_other

        if self.N <= 0:
            self.ax_res.text(0.5, 0.5, "No data", transform=self.ax_res.transAxes,
                             ha="center", va="center")
            self.canvas.draw_idle()
            return

        self.cur = self.cur[:self.N]
        self.res = self.res[:self.N]
        self.force = self.force[:self.N] if self.force else [0.0] * self.N
        self.x = list(range(1, self.N + 1))
        
        # Prepare Other data if available
        if self.has_other:
            self.cur_other = self.cur_other[:self.N_other]
            self.res_other = self.res_other[:self.N_other]
            self.x_other = list(range(1, self.N_other + 1))

        self.fig.suptitle(
            f"{label_text} Contact – Pogo Pin Test Data "
            f"{'(TestMax Vs Other Pin)' if self.has_other else '(TestMax Pin)'}",
            fontsize=16
        )

        # Apply window_size to X-axis: show only the last window_size data points
        # Unless show_all_data is True, then show all data
        if not show_all_data and window_size > 0 and self.N > window_size:
            start_idx = self.N - window_size
            x_display = self.x[start_idx:]
            cur_display = self.cur[start_idx:]
            res_display = self.res[start_idx:]
            force_display = self.force[start_idx:]
            
            x_min = self.x[start_idx]
            x_max = self.x[-1]
            self.display_start_idx = start_idx
        else:
            x_display = self.x
            cur_display = self.cur
            res_display = self.res
            force_display = self.force
            x_min = self.x[0] if self.x else 1
            x_max = self.x[-1] if self.x else window_size
            self.display_start_idx = 0
            
        # Prepare Other display data if available
        if self.has_other:
            if not show_all_data and window_size > 0 and self.N_other > window_size:
                start_idx_other = self.N_other - window_size
                x_display_other = self.x_other[start_idx_other:]
                cur_display_other = self.cur_other[start_idx_other:]
                res_display_other = self.res_other[start_idx_other:]
            else:
                x_display_other = self.x_other
                cur_display_other = self.cur_other
                res_display_other = self.res_other

        # Avoid identical x-limits (single-point data) to prevent warnings
        if x_max == x_min:
            x_min -= 0.5
            x_max += 0.5

        # Current - plot TM
        lw = getattr(self, '_line_width', 1.5)
        self.ax_cur.plot(x_display, cur_display, color=color, linewidth=lw, label='TestMax')
        if self.has_other:
            self.ax_cur.plot(x_display_other, cur_display_other, color=color_other, linewidth=lw, label='Other', linestyle='--')
            self.ax_cur.legend(loc='upper right')
        self.ax_cur.set_ylabel("Current (A)")
        self.ax_cur.set_xlim(x_min, x_max)
        # Snap Y-axis to clean boundaries with padding
        all_cur = list(cur_display)
        if self.has_other:
            all_cur += list(cur_display_other)
        if all_cur:
            data_range = max(all_cur) - min(all_cur)
            # Pick tick step based on data range to keep ~5-7 ticks
            if data_range > 0.1:
                step = 0.05
            elif data_range > 0.05:
                step = 0.02
            else:
                step = 0.01
            factor = int(1 / step)
            cur_lo = math.floor(min(all_cur) * factor) / factor - step
            cur_hi = math.ceil(max(all_cur) * factor) / factor + step
            if (cur_hi - cur_lo) < step * 5:
                mid = (cur_lo + cur_hi) / 2
                cur_lo = round(mid - step * 2.5, len(str(factor)))
                cur_hi = round(mid + step * 2.5, len(str(factor)))
            self.ax_cur.set_ylim(cur_lo, cur_hi)
            self.ax_cur.yaxis.set_major_locator(MultipleLocator(step))
        self.ax_cur.grid(True, linestyle="--", alpha=0.7)

        # Resistance - plot TM
        self.ax_res.plot(x_display, res_display, color=color, linewidth=lw, label='TestMax')
        if self.has_other:
            self.ax_res.plot(x_display_other, res_display_other, color=color_other, linewidth=lw, label='Other', linestyle='--')
            self.ax_res.legend(loc='upper right')
        self.ax_res.set_ylabel("R-Value (mΩ)")
        self.ax_res.set_ylim(0, y_max)
        self.ax_res.set_xlim(x_min, x_max)
        self.ax_res.grid(True, linestyle="--", alpha=0.7)

        # Force / Pressure
        self.ax_force.plot(x_display, force_display, color=color, linewidth=lw)
        self.ax_force.set_xlabel("Test Counts")
        self.ax_force.set_ylabel("Force (grams)")
        self.ax_force.set_xlim(x_min, x_max)
        self.ax_force.grid(True, linestyle="--", alpha=0.7)

        # Cursor - initialize at first visible point
        start_x = x_min
        self.cursor_cur = self.ax_cur.axvline(start_x, lw=1, color=color, alpha=0.7)
        self.cursor_res = self.ax_res.axvline(start_x, lw=1, color=color, alpha=0.7)
        self.cursor_force = self.ax_force.axvline(start_x, lw=1, color=color, alpha=0.7)

        self.info = self.ax_res.text(
            0.02, 0.95, "",
            transform=self.ax_res.transAxes,
            va="top",
            bbox=dict(boxstyle="round", fc="w")
        )
        # Initialize cursor at first visible point
        initial_idx = self.display_start_idx if hasattr(self, 'display_start_idx') else 0
        self._update_info(initial_idx)

        if not getattr(self, "_layout_done", False):
            self.fig.tight_layout(pad=1.0)
            self._layout_done = True
        self.canvas.draw_idle()

    def _update_info(self, idx):
        xpos = self.x[idx]
        self.cursor_cur.set_xdata([xpos, xpos])
        self.cursor_res.set_xdata([xpos, xpos])
        if hasattr(self, "cursor_force"):
            self.cursor_force.set_xdata([xpos, xpos])
        
        info_text = (
            f"Test #: {xpos}\n"
            f"Current TM: {self.cur[idx]:.3f} A\n"
            f"Resistance TM: {self.res[idx]:.2f} mΩ\n"
        )
        
        # Add Other values if available
        if self.has_other and idx < len(self.cur_other):
            info_text += (
                f"Current Other: {self.cur_other[idx]:.3f} A\n"
                f"Resistance Other: {self.res_other[idx]:.2f} mΩ\n"
            )
        
        info_text += f"Force: {self.force[idx]:.2f} g"
        
        self.info.set_text(info_text)

    def _on_move(self, event):
        if event.inaxes not in (self.ax_cur, self.ax_res, self.ax_force):
            return
        if event.xdata is None or self.N <= 0:
            return

        xpos = int(round(event.xdata))
        idx = xpos - 1
        
        if idx < 0:
            idx = 0
        elif idx >= self.N:
            idx = self.N - 1

        self._update_info(idx)
        self.canvas.draw_idle()
