# Manual Accessibility Test Script

Covers keyboard navigation and screen reader behaviour. Automated checks (axe browser extension, jest-axe CI) are separate — this script covers what they cannot.

## Prerequisites

- Backend running: `uvicorn api.main:app --reload` (from project root)
- Frontend running: `npm run dev` (from `frontend/`)
- Open `http://localhost:5173` in the target browser

---

## 1. Keyboard Navigation

Test in any modern browser (Chromium / Edge are fine). No assistive technology required.

### 1.1 Form State (initial page load)

| # | Action | Expected |
|---|--------|----------|
| K1 | Load the page. Press **Tab** repeatedly from the browser address bar. | Focus moves in this order: **map viewport** → **Zoom In** (+) → **Zoom Out** (−) → **Place Pin** → **OpenStreetMap attribution link** → Start Date (DateRangePicker) → **Show Date Picker** (DateRangePicker Start) → End Date (DateRangePicker) → **Show Date Picker** (DateRangePicker End) → Apply → Latitude → Longitude → Start Date (side panel) → End Date (side panel) → Start Time → End Time → Frames Per Day slider → Frame Count → Load Data. The side-panel date and time inputs do **not** show "Show Date Picker" / clock picker buttons — those are hidden so the DateRangePicker on the map panel is the primary date-entry point. |
| K2 | Tab to the **map viewport** and press **Arrow Left**, **Right**, **Up**, **Down**. | Map pans in the corresponding direction (OpenLayers built-in `KeyboardPan` interaction, triggered because `tabindex="0"` is now set on the map target element). |
| K3 | With the map viewport focused, press **+** (or **>**), then **−** (or **<**). | Map zooms in then out (OpenLayers built-in `KeyboardZoom` interaction). |
| K4 | Tab to **Zoom In** and press **Enter** or **Space**. | Map zooms in one level. |
| K5 | Tab to **Zoom Out** and press **Enter** or **Space**. | Map zooms out one level. |
| K6 | Tab to **Place Pin** and press **Enter** or **Space**. | Pin mode activates: button icon changes to the selected-pin image, a red crosshair overlay appears centred on the map, and focus moves automatically to the map viewport. Screen reader announces *"Pin placement tool active. Use arrow keys to pan the map. Press Enter to place a pin at the centre. Press Escape to cancel."* |
| K7 | With pin mode active, use **Arrow keys** to pan (and **+** / **−** to zoom) until the crosshair is over the desired location, then press **Enter**. Alternatively, click anywhere on the map. | Pin is placed at the crosshair centre (or click point). Tool deactivates immediately: icon reverts, crosshair is removed, cursor resets. Screen reader announces *"Pin placed."* — **Cancel path:** press **Escape** or re-activate the **Place Pin** button; tool deactivates without placing a pin and screen reader announces *"Pin placement tool cancelled."* |
| K8 | Tab to the **OpenStreetMap attribution link** and press **Enter**. | Browser follows the OSM copyright link. Return to the app and confirm focus is not permanently lost. |
| K9 | Tab to **Latitude** input. Type `999`. Tab away. | Validation error message appears. Focus does not trap. |
| K10 | Correct the latitude. Tab through to **Load Data** button. Press **Space** or **Enter**. | Data loading begins (progress bar appears). |
| K11 | While loading, Tab to **Cancel** button and press **Enter**. | Loading is cancelled. Form is shown again. |
| K12 | Tab to the **Frames Per Day** slider. Use **Arrow Left / Right** keys. | Slider value changes. Frame Count updates accordingly. |
| K13 | Tab to the **Apply** button in the DateRangePicker. Set an invalid range (end before start) using the keyboard. | Apply button is disabled (not reachable by Enter/Space). Error message is present and announced as text. |

### 1.2 Animation Controls State (after data loads)

Load data first (use default London coordinates, today's date, 48 frames).

| # | Action | Expected |
|---|--------|----------|
| K14 | After load completes, press **Tab**. | Focus order: 3D View → Sky View → Play/Pause → Reset → New Query → Animation Speed slider → (repeats). |
| K15 | Tab to **3D View** button and press **Enter**. Then tab to **Sky View** and press **Enter**. | Active view switches. Button receives the `active` class and its appearance reflects selection. |
| K16 | Tab to **Play/Pause** and press **Enter** to play. Press **Enter** again to pause. | Button label updates to "Pause" then back to "Play". No focus is lost between presses. |
| K17 | Tab to **Reset** and press **Enter**. | Animation resets to the first frame. |
| K18 | Tab to **New Query** and press **Enter**. | Animation controls disappear and the input form is restored. Focus moves to a sensible location in the form (not lost to `<body>`). |
| K19 | Tab to **Animation Speed** slider. Use **Arrow Left / Right** keys. | Speed value changes and the numeric label updates. |

### 1.3 Focus Visibility

| # | Check | Expected |
|---|-------|----------|
| K20 | With keyboard-only navigation throughout all steps above. | Every focused element has a clearly visible focus ring. No element receives focus without a visible indicator. |

---

## 2. Screen Reader

Test with **one** of the following combinations (both are Chromium-based and behave consistently):

- **Edge + Narrator** — built in on Windows, no install needed. Start Narrator: `Win + Ctrl + Enter`.
- **Chrome + NVDA** — free, download from [nvaccess.org](https://www.nvaccess.org). Start NVDA: launch application.

> Firefox is specifically excluded. There is a known issue (#85) where Firefox headless/headed WebGL rendering differs on Windows; combined with NVDA/Firefox quirks around live regions this is not a priority target when Chrome/Edge coverage is in place.

### 2.1 Page Structure

| # | Check | Expected |
|---|-------|----------|
| S1 | Open the page. Use the screen reader's heading navigation (`H` in NVDA/browse mode, or Caps Lock+H in Narrator scan mode). | "Astronomy Animation" is announced as a heading (h1). |
| S2 | Use landmark navigation (NVDA: `D` for landmarks; Narrator: scan mode `R`). | A meaningful main or form landmark is present, so the user can skip directly to the content. |

### 2.2 Form Inputs

| # | Check | Expected |
|---|-------|----------|
| S3 | Tab to **Latitude** input. | Screen reader announces "Latitude, edit, required" (or equivalent). Unit or range constraints (−90 to 90) are not required at this level but are a bonus if present as `aria-describedby`. |
| S4 | Tab to **Longitude** input. | Announced as "Longitude, edit, required". |
| S5 | Tab to **Start Date** (DateRangePicker). | Announced as "Start Date, date edit" or similar. |
| S6 | Tab to **End Date** (DateRangePicker). | Announced as "End Date, date edit". |
| S7 | Tab to **Apply** (DateRangePicker). | Announced as "Apply, button". When disabled, announced as "Apply, button, dimmed" or "unavailable". |
| S8 | Tab to **Frames Per Day** slider. | Announced as "Frames per day, slider, [current value]". Arrow key changes are announced. |
| S9 | Tab to **Frame Count** (readonly). | Announced as "Frame Count, [value], read only". |
| S10 | Tab to **Load Data** button. | Announced as "Load Data, button". When disabled, announced as "dimmed" or "unavailable". |

### 2.3 Validation Errors

| # | Check | Expected |
|---|-------|----------|
| S11 | Enter `999` into Latitude and Tab away. | Error message "Latitude must be between −90° and 90°" is announced. It does not require the user to navigate to it manually — it appears inline near the input so virtual-cursor reading encounters it naturally. |
| S12 | Set DateRangePicker end date before start date and Tab away. | Error message "Start date must be before end date." is announced. The Apply button state change (disabled) is also communicated. |

### 2.4 Loading State

| # | Check | Expected |
|---|-------|----------|
| S13 | Click/activate **Load Data**. Immediately read the page. | "Loading data…" text is present and readable. Progress percentage is visible in text form (no screen-reader-only announcement is required, but the text must be reachable by virtual cursor). |
| S14 | Tab to **Cancel** button while loading. | Announced as "Cancel, button". Activating it stops loading and returns to the form. |

### 2.5 Map Viewport

| # | Check | Expected |
|---|-------|----------|
| S21 | Tab to the **map viewport** (the first focusable element on the page). | Screen reader announces "Interactive map, application" (role + label). Immediately after the label, the description "Interactive map. Use the zoom controls or scroll to zoom. Click to place a pin when the pin tool is active." is read (via `aria-describedby`). |
| S22 | While the map viewport is focused, press **Arrow** keys. | Map pans. No screen reader announcement is expected for individual pan steps — this is an `application` region. |
| S23 | Tab away from the map viewport to the **Zoom In** button. | Announced as "Zoom In, button" (or the OL default "Zoom in" label). Focus leaves the application region cleanly. |

### 2.6 Animation Controls

| # | Check | Expected |
|---|-------|----------|
| S15 | After load completes, Tab to **3D View** button. | Announced as "3D View, button" (or "3D View, button, pressed" if aria-pressed is set). |
| S16 | Tab to **Sky View** button. | Announced as "Sky View, button". |
| S17 | Tab to **Play/Pause** button. | Announced as "Play, button" or "Pause, button" reflecting the current state. |
| S18 | Tab to **Reset** and **New Query** buttons. | Each announced by its visible label. |
| S19 | Tab to **Animation Speed** slider. | Announced as "Animation Speed, slider, [value]". |
| S20 | Navigate the current-info section by virtual cursor. | Time, Sun Alt, Sun Visible, Moon Alt, Moon Visible, Moon Phase, Illumination are all readable as text. No information is conveyed only by colour or visual position. |

---

## 3. Pass / Fail Criteria

- **Pass**: All checks in section 1 and at least one screen reader combination from section 2 pass.
- **Fail**: Any focusable control is unreachable by keyboard, any focus indicator is invisible, any form label/error is not announced by the screen reader, or the map viewport is not announced with a meaningful name and role.

Record results in a simple table or inline notes. Link to the relevant GitHub issue for any failures found.
