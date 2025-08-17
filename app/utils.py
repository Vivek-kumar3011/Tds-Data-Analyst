
import io, base64, time
from typing import Tuple

def time_budget_ok(start_time: float, budget_seconds: float = 160.0) -> bool:
    """Keep a margin inside the 3-minute limit; return False if budget exceeded."""
    return (time.monotonic() - start_time) < budget_seconds

def fig_to_base64_png(fig, max_bytes: int = 100_000, dpi: int = 110) -> str:
    """Encode a Matplotlib figure as base64 PNG under size limit. Adjust dpi if needed."""
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    # Try a couple of DPIs to get under size limit
    for try_dpi in (dpi, 100, 90, 80, 70):
        buf.seek(0); buf.truncate(0)
        fig.savefig(buf, format='png', dpi=try_dpi, bbox_inches='tight', pad_inches=0.1)
        data = buf.getvalue()
        if len(data) <= max_bytes:
            b64 = base64.b64encode(data).decode('ascii')
            plt.close(fig)
            return f"data:image/png;base64,{b64}"
    # If still too big, downscale aggressively
    buf.seek(0); buf.truncate(0)
    fig.savefig(buf, format='png', dpi=60, bbox_inches='tight', pad_inches=0.05)
    data = buf.getvalue()
    b64 = base64.b64encode(data).decode('ascii')
    plt.close(fig)
    return f"data:image/png;base64,{b64}"
