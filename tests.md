# ITU Noticeboard Patrol: Test Scenarios & Implementation Plan

**Based on Requirements Analysis of:**
- `8130706.pdf` (Primary: Gemini API & Revisiting Logic)
- `8064833.pdf` (Secondary: Core Navigation & Anomaly Detection)

## 1. System High-Level Overview
The system is an autonomous mobile robot (TurtleBot-class) that patrols university corridors to inspect noticeboards. It utilizes **Google Gemini API** (Cloud VLM) for intelligent content extraction and anomaly detection (expired/duplicate posters). A key feature is the **Persistent Memory** and **Revisiting Logic**, where the robot re-inspects boards flagged as "Expired" to verify their status.

## 2. Use Case Scenarios (Test Scenarios)

### Scenario 1: Standard Patrol & Successful Extraction (Happy Path)
**Goal:** Verify end-to-end flow from navigation to logging.
1. **Action**: Robot navigates to `Board_ID_1`.
2. **Action**: Robot aligns and stops at ~50cm distance.
3. **Action**: Captures high-res image.
4. **Processing**: Sends image to Gemini API.
5. **Result**: API returns Valid JSON `{ "title": "Chess Club", "date": "2025-12-25", "expired": false, "duplicate": false }`.
6. **Action**: Information is logged to `Persistent Memory`.
7. **Action**: Robot proceeds to next board.

### Scenario 2: Expired Poster Detection & Revisit Scheduling
**Goal:** Verify anomaly detection and planner logic update.
1. **Action**: Robot approaches encounters a poster with an old date (e.g., "Nov 2024").
2. **Processing**: Gemini API analyzes date vs. current date.
3. **Result**: API returns `{ "is_expired": true }`.
4. **Action**: System flags `Board_ID_X` as **STATUS: EXPIRED** in Memory.
5. **Action**: Planner adds `Board_ID_X` to the **Re-inspection Queue**.
6. **Action**: Robot generally continues patrol (or completes loop).
7. **Revisit Phase**: Robot navigates *back* to `Board_ID_X` to check if it has been removed.

### Scenario 3: Duplicate Announcement Detection
**Goal:** Verify cross-board memory comparison.
1. **Context**: `Board_A` was previously scanned and logged "Math Exam Schedule".
2. **Action**: Robot scans `Board_B`.
3. **Result**: Gemini API (or local logic comparing content) identifies the content is identical. (Note: Doc implies Cloud might do this, or Memory logic).
   - *Refined Logic*: If Gemini returns a summary, the System checks Memory for matching titles/dates.
4. **Action**: Flag `Board_B` as **STATUS: DUPLICATE**.
5. **Action**: Log potential spam/waste usage.

### Scenario 4: Dynamic Obstacle Avoidance
**Goal:** Verify Navigation Safety.
1. **Action**: Robot navigates between boards.
2. **Condition**: A pedestrian (simulated actor) crosses the path.
3. **Reaction**: Robot slows down or re-plans path.
4. **Result**: No collision; Robot resumes path to target.

### Scenario 5: API Failure / Network Issues (Resiliency)
**Goal:** Verify robustness against cloud dependencies.
1. **Action**: Robot attempts to call Gemini API.
2. **Condition**: Internet connection lost or API 500 Error.
3. **Reaction**:
   - System logs "API Error".
   - Flags board as "Unclear" or "Pending Retry".
   - Does *not* crash node.
   - Continues to next board.

### Scenario 6: Multiple Posters on Single Board (1 ArUco -> N Posters)
**Goal:** Verify the system can extract multiple distinct announcements from a single captured view/location.
1. **Context**: A single physical noticeboard (marked by one ArUco or location) contains **3 different flyers** (e.g., "Chess Club", "Math Exam", "Lost Item").
2. **Action**: Robot docks and captures the high-res image of the entire board.
3. **Processing**: Send image to Gemini API with a prompt to "Identify and list *all* distinct announcements".
4. **Result**: API returns a JSON *Array* of objects: `[ {title: "Chess", ...}, {title: "Math", ...}, ... ]`.
5. **Action**: Memory handles logging multiple entries for a single `Board_ID`.
6. **Edge Case**: One flyer is expired, others are valid. System must only flag the specific expired flyer, not invalidate the whole board (unless physically necessary).

### Scenario 7: Dense Corridor Distribution
**Goal:** Verify navigation and logic when boards are clustered closely (e.g., every 1 meter).
1. **Context**: A simulated hallway with 5 boards placed in rapid succession.
2. **Action**: Robot must visit Board 1 -> Dock -> Analyze -> Undock -> Visit Board 2.
3. **Test**: Ensure the "Undock/Recovery" maneuver is tight enough to not miss the immediate next target (Board 2) or collide with it while backing up.
4. **Result**: All 5 boards are successfully visited and logged; none are skipped due to "goal reached" tolerance overlaps.

## 3. Coverage Test Plan

To ensure robustness, we will test under the following conditions:

| ID | Test Condition | Expected Outcome |
|----|---------------|------------------|
| **C1** | **Lighting Variation** | Detection should work in standard and slightly dimmed lighting (Gazebo environment settings). |
| **C2** | **Approach Angle** | Robot should correct orientation if it arrives at a sharp angle (Visual Servoing). |
| **C3** | **Empty Board** | API should return neutral status ("No Content" or similar) without error. |
| **C4** | **Revisit Execution** | Planner must specifically generate a path to *only* the specific target board in the second phase. |
| **C5** | **Memory Persistence** | If the robot is restarted, it should remember which boards were scanned (optional based on implementation depth, but recommended). |

## 4. Implementation Analysis & Roadmap

Based on the current state of the codebase (examined in previous conversations) vs. Requirements:

### Current Status
- **Navigation**: Basic patrol exists.
- **Perception**: Initial Gemini integration exists (but faced model naming issues).
- **Planner**: Basic sequencing exists.

### Missing / To Be Improved
1.  **Revisiting Logic (The "Loop")**:
    - *Requirement*: "A high-level planner that schedules visits to boards previously flagged...".
    - *Task*: Implement a state machine in the Planner: `PHASE_SCAN` -> `PHASE_ANALYZE_RESULTS` -> `PHASE_REVISIT`.
2.  **Persistent Memory**:
    - *Requirement*: Store `Board ID`, `Status`, `Attributes`.
    - *Task*: Create a `MemoryNode` or a shared data structure (JSON/Database) that persists across the session.
3.  **Visual Servoing (Fine Positioning)**:
    - *Requirement*: "Switches to visual servoing behavior to stop... and face board frontally".
    - *Task*: Ensure the robot doesn't just go to a coordinate but uses the camera feed (or precise orientation goal) to align perfectly.
4.  **Anomaly Logic**:
    - *Requirement*: Explicit checking for Duplicates.
    - *Task*: Logic to compare current `extract` vs `history`.

## 5. Next Steps for Development
1. **Refine Gemini Prompt**: Ensure it returns the required JSON structure `{title, date, is_expired, is_duplicate}` consistently.
2. **Implement Memory Module**: a Python class/node to store results.
3. **Upgrade Planner Node**: Add the `Revisit` logic.
