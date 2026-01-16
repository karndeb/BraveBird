# Bravebird: Record and Replay System

![Bravebird System Architecture](https://github.com/karndeb/BraveBird/blob/master/arch%20diagram/system-arch%20V2.png)

## Part 1: Core Design Patterns for Optimization

To make "Bravebird" fly, we will apply these four high-performance patterns:

### 1. The Actor Model (Concurrency)
Instead of a single while loop running everything, we split the brain into independent Actors that communicate via queues.

*   **Perception Actor:** Constantly looking at the screen (UI-Ins).
*   **Cognition Actor:** Planning the next move (Gemini).
*   **Action Actor:** Clicking/Typing (Arrakis/Bridge).
*   **Benefit:** The Perception Actor can process the result of a click while the Cognition Actor is still logging the previous thought.

### 2. Event Sourcing (State Management)
Instead of storing the "Current State" as a variable, we store a Log of Events.

*   **Event:** UserClicked, ScreenUpdated, ElementFound, ErrorOccurred.
*   **Benefit:** This makes the Data Flywheel trivial. You don't need to "extract" training data later; the Event Log *is* the training data.

### 3. Speculative Execution (Latency Hiding)
*   **Concept:** While the Agent is waiting for the UI to update after a click, it should already be calculating the likely next step based on the plan.
*   **Application:** The Synthesizer generates a plan. When Step 1 executes, the Grounding Model (UI-Ins) immediately starts scanning for the Step 2 target, even before Step 1 is confirmed finished.

### 4. Circuit Breaker (Robustness)
*   **Concept:** If a subsystem fails repeatedly, cut the connection to prevent cascading crashes.
*   **Application:** If the Arrakis Sandbox stops responding to health checks, the Circuit Breaker trips, triggers a `hard_reset` of the VM, and rewinds the Agent to the last snapshot automatically.

---

## Part 2: The Optimized "Async-Actor" Architecture

We go with a **Publish-Subscribe (Pub/Sub) System** using Redis or ZeroMQ as the nervous system connecting Windows and WSL.

### The Central Nervous System (Redis/ZeroMQ)
*   **Channel `vision_stream`:** Raw encoded frames (JPEG).
*   **Channel `input_events`:** Mouse/Keyboard interrupts.
*   **Channel `control_signals`:** Commands ("Stop", "Replay", "Snapshot").

### The Actors (Running in Parallel)

**1. The Observer Actor (Windows Host)**
*   **Pattern:** Producer.
*   **Logic:** It does not wait. It blasts compressed frames and input coordinates into the Redis Bus as fast as possible.
*   **Optimization:** Uses Delta Encoding. Only sends screen frames if pixels have changed significantly.

**2. The Synthesizer Pipeline (WSL - Stream Processing)**
*   **Pattern:** Pipe & Filter.
*   **Logic:** It doesn't wait for the recording to finish. It processes the stream live.
    *   Frame -> OmniParser (Filter) -> Detected Elements.
    *   This means when the user hits "Stop Recording," the processing is already 90% done.

**3. The Executor Actor (WSL)**
*   **Pattern:** Finite State Machine (FSM).
*   **States:** `IDLE` -> `OBSERVING` -> `THINKING` -> `ACTING` -> `VERIFYING` -> `RECOVERING`.
*   **Logic:**
    *   **Async Grounding:** Calls UI-Ins. While waiting for the coordinate, it prefetches the accessibility tree.
    *   **Optimistic UI:** If the plan says "Type 'Hello'", it sends the keystrokes immediately after the click without waiting for a visual confirmation of the text box focus (unless verification fails).

---

## Part 3: Critical Engineering Optimizations

1.  **Protocol Buffers (Protobuf) over JSON:**
    *   Instead of sending heavy JSON text over the local network between Windows and WSL, use Protobuf. It's smaller and faster to serialize/deserialize.

2.  **Shared Memory (SHM) for Video:**
    *   Redis is fast, but sending images is heavy.
    *   **Optimization:** The Windows Recorder writes raw frames to a Shared Memory Segment (or a memory-mapped file). The WSL Perception Actor reads directly from that memory address. This achieves **Zero-Copy latency**.

3.  **KV-Cache for the Planner:**
    *   Gemini Flash supports context caching.
    *   **Optimization:** Cache the system prompt and the static parts of the workflow history. You only send the *new* screenshot and *new* error logs. This reduces API latency by ~40%.
