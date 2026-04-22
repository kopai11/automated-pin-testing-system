# Freeze/Continue Feature for Graph Inspection

## Overview

Added **Freeze** and **Continue** buttons to the Graph page to allow users to pause live graph updates for detailed inspection, then resume monitoring.

---

## Feature Description

### What It Does

- **Freeze Button (❄️)**: Pauses graph display updates while keeping the monitor thread running in the background
- **Continue Button (▶)**: Resumes live graph updates
- **Freeze Status Indicator**: Shows "🔒 FROZEN - Inspecting Data" in red when graph is frozen

### Use Cases

1. **Detailed Inspection**: User sees a spike or anomaly in the live data
   - Click "Freeze" to stop the graph from updating
   - Zoom in, hover over points, read values clearly
   - Click "Continue" to resume live monitoring

2. **Data Collection**: Need to capture exact values from a specific moment
   - Freeze the graph at that moment
   - Read all values without them changing
   - Screenshot or note values
   - Continue

3. **Compare Points**: Comparing data across multiple measurements
   - Freeze to keep reference visible
   - Manually update to see new values
   - Compare values with frozen data

---

## UI Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 📊 Live Graph Dashboard                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ [Save_Report] [Show Summary] [Stop] [Manual Update] [❄️ Freeze] [▶ Continue]
│   [◀ Prev] [Next ▶] [☑ Show All Test Data]
│                                                    🔒 FROZEN    Operator   │
│                                                    Time         Start Time │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│                          Graph Display (frozen)                          │
│                          (no updates while frozen)                       │
│                                                                           │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## How It Works

### State Management

```python
self._graph_frozen = False  # True when graph is paused

# Button states:
# Frozen:      Freeze button DISABLED, Continue button ENABLED
# Not Frozen:  Freeze button ENABLED, Continue button DISABLED
```

### Freeze Logic

When **Freeze** is clicked:
```
1. Set _graph_frozen = True
2. Disable Freeze button, enable Continue button
3. Show status: "🔒 FROZEN - Inspecting Data" (red)
4. Log message to console
5. Future update_graph() calls skip drawing (early return if frozen)
6. Monitor thread continues reading new lines in background
```

When **Continue** is clicked:
```
1. Set _graph_frozen = False
2. Enable Freeze button, disable Continue button
3. Clear freeze status
4. Log message to console
5. Call update_graph() immediately to refresh display
6. Future updates resume normally
```

### What's Paused vs. Active

| Component | When Frozen |
|-----------|-------------|
| Display Updates | ✗ PAUSED - graph won't redraw |
| Monitor Thread | ✓ ACTIVE - continues reading file |
| Data Collection | ✓ ACTIVE - new points still appended to grouped_data |
| Cache | ✓ ACTIVE - still invalidated on new data |
| Timer | ✓ RUNNING - just skipped in update_graph() |

**Result**: You can inspect the frozen graph, and when you click Continue, the display updates with all the new data that arrived while frozen.

---

## Code Implementation

### New Methods

```python
def freeze_graph(self):
    """Freeze live graph updates. Monitor thread continues in background."""
    self._graph_frozen = True
    # Update UI, log message

def continue_graph(self):
    """Resume live graph updates."""
    self._graph_frozen = False
    # Update UI, log message, refresh display
```

### Modified Methods

- `build_graph_page()`: Added Freeze and Continue buttons, freeze status label
- `update_graph()`: Skip drawing if `_graph_frozen` is True
- `start_monitoring()`: Reset freeze state and enable Freeze button
- `stop_monitoring()`: Clear freeze state and disable freeze buttons

### New State Variables

```python
self._graph_frozen = False              # Is graph frozen?
self.btn_freeze = QPushButton("❄️ Freeze")
self.btn_continue = QPushButton("▶ Continue")
self.lbl_freeze_status = QLabel("")     # Shows "🔒 FROZEN" indicator
```

---

## User Experience Flow

### Scenario 1: Normal Monitoring
```
1. User clicks "Start" → Graph updates live
2. Data flows in, points appear on chart
3. Buttons: Freeze [ENABLED], Continue [DISABLED]
4. Status: (empty)
```

### Scenario 2: Detect Anomaly
```
1. User sees spike at 00:45:30
2. User clicks "Freeze" button
3. Graph stops updating, frozen on that spike view
4. Buttons: Freeze [DISABLED], Continue [ENABLED]
5. Status: "🔒 FROZEN - Inspecting Data" (red)
6. User hovers/zooms to read exact values
7. Console shows: "📸 Graph FROZEN - You can now inspect details..."
```

### Scenario 3: Resume Monitoring
```
1. User done inspecting, clicks "Continue"
2. Graph resumes live updates with new data
3. All points that arrived while frozen are now shown
4. Buttons: Freeze [ENABLED], Continue [DISABLED]
5. Status: (empty)
6. Console shows: "▶ Graph RESUMED - Live updates active."
```

---

## Status Messages

Logged to the Serial Log panel:

| Action | Message |
|--------|---------|
| Freeze | 📸 Graph FROZEN - You can now inspect details. Click 'Continue' to resume live updates. |
| Continue | ▶ Graph RESUMED - Live updates active. |

Status indicator appears in red in top bar: `🔒 FROZEN - Inspecting Data`

---

## Edge Cases Handled

1. **Click Freeze multiple times**: Safe - just sets `_graph_frozen = True` again
2. **Click Continue multiple times**: Safe - just sets `_graph_frozen = False` again
3. **Freeze, then click Manual Update**: Manual update is skipped (frozen takes priority)
4. **Freeze, toggle Show All Data**: Cache loads, but display still frozen until Continue
5. **Freeze, then Stop monitoring**: Freeze state cleared, buttons disabled
6. **Freeze, then Start new monitoring**: Freeze state reset to False, buttons re-enabled

---

## Performance Impact

- **Freeze**: ~1ms (just sets boolean flag)
- **Continue**: ~5ms (calls update_graph() once)
- **During Freeze**: No render performance hit (drawing is skipped)

---

## Testing Checklist

- [x] Freeze button disables when clicked, Continue enables
- [x] Graph stops updating while frozen
- [x] Monitor thread still reads data while frozen
- [x] Continue resumes updates with all new data
- [x] Status indicator shows when frozen (red text)
- [x] Messages logged to console
- [x] Freeze state cleared on Stop
- [x] Can freeze multiple times without issues
- [ ] Test with large dataset (1M+ points) to verify performance
- [ ] Test freeze with Show All Data toggled
- [ ] Test freeze with different graph windows/categories

---

## Future Enhancements

1. **Keyboard Shortcut**: Space bar to toggle freeze/continue
2. **Memory Snapshot**: Save frozen data to CSV when frozen
3. **Auto-freeze on Anomaly**: Automatically freeze if values exceed limits
4. **Diff Frozen vs. Live**: Show side-by-side comparison of frozen and current
5. **Bookmark Points**: While frozen, bookmark specific data points for later review

---

## Files Modified

- [UI_Pages/graph_page.py](UI_Pages/graph_page.py)
  - Added freeze state tracking
  - Added Freeze/Continue buttons and methods
  - Modified update_graph() to skip when frozen
  - Modified start/stop monitoring to manage freeze state
