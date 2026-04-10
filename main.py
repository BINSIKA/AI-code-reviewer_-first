"""
main.py
Full Reflex web application — AI Code Reviewer.
Pages: Home | Review Code | AI Assistant | History | About

Run:
    cd ai_reviewer_app
    reflex init
    reflex run
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import reflex as rx
import httpx
import json
from datetime import datetime

from ai_reviewer_app.components.navbar import navbar

# ── API base URL (FastAPI server running separately) ──────────────
API_URL = "http://localhost:8000"

# ── Demo snippets per language ────────────────────────────────────
DEMO_SNIPPETS: dict[str, str] = {
    "python": """import os
import sys
import json

def calculate_average(numbers):
    totl = 0
    unused_var = "never used"
    for n in numbers:
        totl += n
    averag = totl / len(numbers)
    return averag

def unused_function():
    pass

result = calculate_average([10, 20, 30, 40])
print("Average:", result)""",

    "javascript": """const express = require('express');
const fs = require('fs');

function getUserData(userId) {
  var unusedVar = "hello";
  let data = [];
  for (var i = 0; i < 100; i++) {
    for (var j = 0; j < 100; j++) {
      data.push(i * j);
    }
  }
  return data;
}

function unusedHelper() {
  return null;
}

console.log(getUserData(1));""",

    "java": """import java.util.ArrayList;
import java.util.HashMap;
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        String unusedStr = "never used";
        ArrayList<Integer> numbers = new ArrayList<>();
        for (int i = 0; i < 10; i++) {
            numbers.add(i * i);
        }
        int total = 0;
        for (int n : numbers) total += n;
        System.out.println("Sum: " + total);
    }
    private static void unusedMethod() {}
}""",

    "go": """package main

import (
    "fmt"
    "os"
    "strings"
)

func calculate(nums []int) int {
    total := 0
    for i := 0; i < len(nums); i++ {
        total += nums[i]
    }
    return total
}

func unusedFunc() string {
    return "never called"
}

func main() {
    nums := []int{1, 2, 3, 4, 5}
    fmt.Println("Total:", calculate(nums))
}""",
}

LANGUAGES = ["python", "javascript", "typescript", "java", "c", "cpp", "go", "rust"]


# ══════════════════════════════════════════════════════════════════
#  STATE
# ══════════════════════════════════════════════════════════════════

class HistoryItem(rx.Base):
    ts: str = ""
    language: str = ""
    grade: str = ""
    issue_count: int = 0
    summary: str = ""
    original_code: str = ""
    corrected_code: str = ""
    expanded: bool = False


class ChatMessage(rx.Base):
    role: str = ""   # "user" | "assistant"
    content: str = ""


class State(rx.State):
    # ── Review page ──
    code_input: str = ""
    language: str = "python"
    is_loading: bool = False
    analysis_done: bool = False

    # Results
    grade: str = "N/A"
    issue_count: int = 0
    syntax_msg: str = ""
    syntax_status: str = ""
    summary: str = ""
    corrected_code: str = ""
    optimizations: list[str] = []
    detected_bugs: list[str] = []
    issues: list[str] = []
    unused_imports: list[str] = []
    unused_functions: list[str] = []
    unused_variables: list[str] = []
    style_violations: list[str] = []
    created_vars: list[str] = []
    used_vars: list[str] = []
    linter_tools: list[str] = []   # stored as "name|desc"
    progress_label: str = ""

    # ── Assistant page ──
    chat_messages: list[ChatMessage] = []
    chat_input: str = ""
    is_chatting: bool = False
    chat_context: str = ""

    # ── History page ──
    history: list[HistoryItem] = []

    # ── Setters ──
    def set_language(self, val: str):
        self.language = val

    def set_chat_input(self, val: str):
        self.chat_input = val

    def load_demo(self):
        self.code_input = DEMO_SNIPPETS.get(self.language, DEMO_SNIPPETS["python"])

    def toggle_history_item(self, idx: int):
        self.history[idx].expanded = not self.history[idx].expanded

    def clear_history(self):
        self.history = []

    def clear_chat(self):
        self.chat_messages = []
        self.chat_context = ""

    # ── Main Analysis ─────────────────────────────────────────────

    async def run_full_review(self):
        if not self.code_input.strip():
            yield rx.window_alert("Please paste some code first!")
            return

        self.is_loading = True
        self.analysis_done = False
        self.progress_label = "Running syntax detection..."
        yield

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                self.progress_label = "Running static analysis..."
                yield

                resp = await client.post(
                    f"{API_URL}/analyze",
                    json={"code": self.code_input, "language": self.language},
                )

                if resp.status_code != 200:
                    yield rx.window_alert(f"API Error {resp.status_code}: {resp.text}")
                    self.is_loading = False
                    return

                data = resp.json()

                self.progress_label = "Processing AI suggestions..."
                yield

                # Populate state
                self.grade          = data.get("grade", "N/A")
                self.issue_count    = data.get("issue_count", 0)
                self.syntax_msg     = data.get("syntax_msg", "")
                self.syntax_status  = data.get("syntax_status", "")
                self.summary        = data.get("summary", "")
                self.corrected_code = data.get("corrected_code", "")
                self.optimizations  = data.get("optimizations", [])
                self.detected_bugs  = data.get("detected_bugs", [])
                self.unused_imports   = data.get("unused_imports", [])
                self.unused_functions = data.get("unused_functions", [])
                self.unused_variables = data.get("unused_variables", [])
                self.style_violations = data.get("style_violations", [])
                self.created_vars     = data.get("created_vars", [])
                self.used_vars        = data.get("used_vars", [])

                # Issues as plain strings
                raw_issues = data.get("issues", [])
                self.issues = [
                    f"Line {i.get('line',0)}: {i.get('text','')}"
                    for i in raw_issues
                ]

                # Linter tools as "name|desc" strings
                self.linter_tools = [
                    f"{t['name']}|{t['desc']}"
                    for t in data.get("linter_tools", [])
                ]

                # Build chat context for AI assistant
                self.chat_context = (
                    f"Language: {data.get('language_display','')}\n"
                    f"Grade: {self.grade} | Issues: {self.issue_count}\n"
                    f"Summary: {self.summary}\n"
                    f"Issues: {', '.join(self.issues[:5]) or 'None'}\n"
                    f"Original Code:\n{self.code_input[:800]}"
                )

                # Save to history
                self.history.insert(0, HistoryItem(
                    ts=datetime.now().strftime("%H:%M:%S"),
                    language=self.language,
                    grade=self.grade,
                    issue_count=self.issue_count,
                    summary=self.summary,
                    original_code=self.code_input,
                    corrected_code=self.corrected_code,
                    expanded=False,
                ))

                self.analysis_done = True

        except httpx.ConnectError:
            yield rx.window_alert(
                "Cannot reach the API server.\n\n"
                "Make sure server.py is running:\n"
                "  python server.py"
            )
        except Exception as e:
            yield rx.window_alert(f"Error: {str(e)}")
        finally:
            self.is_loading = False
            self.progress_label = ""

    # ── Chat ─────────────────────────────────────────────────────

    async def send_chat(self):
        msg = self.chat_input.strip()
        if not msg or self.is_chatting:
            return

        self.is_chatting = True
        self.chat_input = ""
        self.chat_messages.append(ChatMessage(role="user", content=msg))
        yield

        # Build history list for API
        history_payload = [
            {"role": m.role, "content": m.content}
            for m in self.chat_messages[:-1]
        ]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{API_URL}/chat",
                    json={
                        "message": msg,
                        "context": self.chat_context,
                        "history": history_payload,
                    },
                )
                reply = resp.json().get("reply", "No response.")
        except Exception as e:
            reply = f"⚠️ Error: {str(e)}"

        self.chat_messages.append(ChatMessage(role="assistant", content=reply))
        self.is_chatting = False


# ══════════════════════════════════════════════════════════════════
#  UI HELPERS
# ══════════════════════════════════════════════════════════════════

PAGE_BG   = {"background": "#0a0e1a", "min_height": "100vh", "color": "#e2e8f8"}
CONTAINER = {"max_width": "1000px", "padding": "2rem 1.5rem 4rem"}
CARD      = {"background": "#0f1628", "border": "1px solid #1e2d52",
             "border_radius": "12px", "padding": "1.25rem",
             "margin_bottom": "1rem"}
CARD_DARK = {**CARD, "background": "#141c35"}

H1 = {"font_size": "28px", "font_weight": "700", "letter_spacing": "-.01em",
      "margin_bottom": "6px"}
LABEL = {"font_size": "11px", "color": "#4a5a8a", "text_transform": "uppercase",
         "letter_spacing": ".07em", "margin_bottom": "6px"}


def _section_card(icon_text: str, title: str, *children, border_color="#1e2d52") -> rx.Component:
    return rx.box(
        rx.flex(
            rx.text(icon_text, font_size="14px"),
            rx.text(title, font_size="13px", font_weight="600", color="#e2e8f8"),
            align="center", gap="8px",
            padding="12px 18px",
            border_bottom="1px solid #1e2d52",
            background="#141c35",
            border_radius="12px 12px 0 0",
        ),
        rx.box(*children, padding="1rem 1.25rem"),
        border=f"1px solid {border_color}",
        border_radius="12px",
        overflow="hidden",
        margin_bottom="1rem",
    )


def _pill(text: str, color: str) -> rx.Component:
    return rx.box(
        rx.text(text, font_size="11px", font_family="monospace"),
        background="#1a2340",
        border=f"1px solid {color}44",
        border_radius="5px",
        padding="2px 8px",
        color=color,
        display="inline-block",
        margin="2px",
    )


def _issue_row(text: str) -> rx.Component:
    return rx.flex(
        rx.box(width="7px", height="7px", border_radius="50%",
               background="#fbbf24", flex_shrink="0", margin_top="6px"),
        rx.text(text, font_size="13px", color="#8899cc"),
        gap="10px", padding="6px 0",
        border_bottom="1px solid #1e2d5222",
    )


def _grade_color(grade_val: str) -> str:
    colors = {"A": "#22c55e", "B": "#2dd4bf", "C": "#fbbf24", "D": "#f87171"}
    return colors.get(grade_val, "#4a5a8a")


# ══════════════════════════════════════════════════════════════════
#  PAGE: HOME
# ══════════════════════════════════════════════════════════════════

def index() -> rx.Component:
    return rx.box(
        navbar(),
        rx.container(
            # Hero
            rx.vstack(
                rx.box(
                    rx.text(
                        "✓ AI-Powered • 8 Languages",
                        font_size="11px", letter_spacing=".1em",
                        text_transform="uppercase", color="#4f8ef7",
                    ),
                    background="rgba(79,142,247,.1)",
                    border="1px solid rgba(79,142,247,.2)",
                    padding="4px 14px",
                    border_radius="20px",
                    display="inline-block",
                    margin_bottom="1.5rem",
                ),
                rx.heading(
                    "Code review that is fast,\nclear, and reliable.",
                    size="8",
                    font_weight="700",
                    text_align="center",
                    color="#e2e8f8",
                    letter_spacing="-.02em",
                ),
                rx.text(
                    "Analyze multilingual code with static checks, external diagnostics,"
                    " and AI insights without context switching.",
                    color="#8899cc", font_size="17px",
                    text_align="center", max_width="540px",
                    line_height="1.7",
                ),
                rx.flex(
                    rx.link(
                        rx.button(
                            "▶ Open Review Workspace",
                            background="#4f8ef7", color="white",
                            border_radius="8px", padding="11px 22px",
                            font_size="14px", cursor="pointer",
                            _hover={"background": "#3a6fd4"},
                        ),
                        href="/posts",
                    ),
                    rx.link(
                        rx.button(
                            "? Ask the Assistant",
                            background="#141c35", color="#e2e8f8",
                            border="1px solid #243460",
                            border_radius="8px", padding="11px 22px",
                            font_size="14px", cursor="pointer",
                            _hover={"border_color": "#4f8ef7", "color": "#4f8ef7"},
                        ),
                        href="/assistant",
                    ),
                    gap="12px", justify="center", flex_wrap="wrap",
                ),
                rx.text(
                    "Supports 8 languages with static and external diagnostics.",
                    font_size="12px", color="#4a5a8a",
                ),
                # Stats
                rx.grid(
                    rx.box(
                        rx.text("8", font_size="28px", font_weight="700",
                                color="#4f8ef7", font_family="monospace"),
                        rx.text("Languages", font_size="11px", color="#4a5a8a",
                                text_transform="uppercase", letter_spacing=".05em"),
                        **CARD, text_align="center",
                    ),
                    rx.box(
                        rx.text("5", font_size="28px", font_weight="700",
                                color="#4f8ef7", font_family="monospace"),
                        rx.text("Analysis Layers", font_size="11px", color="#4a5a8a",
                                text_transform="uppercase", letter_spacing=".05em"),
                        **CARD, text_align="center",
                    ),
                    rx.box(
                        rx.text("AI", font_size="28px", font_weight="700",
                                color="#4f8ef7", font_family="monospace"),
                        rx.text("Powered", font_size="11px", color="#4a5a8a",
                                text_transform="uppercase", letter_spacing=".05em"),
                        **CARD, text_align="center",
                    ),
                    columns="3", gap="12px", width="100%", max_width="520px",
                ),
                align="center", spacing="5", padding="3.5rem 1rem 2rem",
            ),
            **CONTAINER,
        ),
        **PAGE_BG,
    )


# ══════════════════════════════════════════════════════════════════
#  PAGE: REVIEW CODE  (/posts)
# ══════════════════════════════════════════════════════════════════

def posts() -> rx.Component:
    return rx.box(
        navbar(),
        rx.container(
            rx.vstack(
                # ── Header ──
                rx.heading("Review Code", **H1),
                rx.text(
                    "Paste code in any supported language and run static checks,"
                    " external tool diagnostics, and AI-assisted improvements.",
                    color="#8899cc", font_size="14px",
                ),

                # ── Controls ──
                rx.flex(
                    rx.vstack(
                        rx.text("Language", **LABEL),
                        rx.select(
                            LANGUAGES,
                            value=State.language,
                            on_change=State.set_language,
                            background="#0f1628",
                            color="#e2e8f8",
                            border="1px solid #243460",
                            border_radius="8px",
                            padding="9px 14px",
                            font_size="13px",
                        ),
                        spacing="1",
                    ),
                    rx.flex(
                        rx.button(
                            rx.cond(State.is_loading, "Analyzing...", "▶ Analyze Code"),
                            on_click=State.run_full_review,
                            loading=State.is_loading,
                            background="#4f8ef7",
                            color="white",
                            border_radius="8px",
                            padding="9px 18px",
                            font_size="13px",
                            cursor="pointer",
                            _hover={"background": "#3a6fd4"},
                        ),
                        rx.button(
                            "Load Demo",
                            on_click=State.load_demo,
                            background="#141c35",
                            color="#e2e8f8",
                            border="1px solid #243460",
                            border_radius="8px",
                            padding="9px 18px",
                            font_size="13px",
                            cursor="pointer",
                        ),
                        gap="8px",
                        align="flex-end",
                    ),
                    justify="between",
                    align="flex-end",
                    width="100%",
                    gap="12px",
                ),

                # ── Code textarea ──
                rx.text_area(
                    placeholder="# Paste your code here...",
                    value=State.code_input,
                    on_change=State.set_code_input,
                    width="100%",
                    height="260px",
                    background="#0f1628",
                    color="#e2e8f8",
                    border="1px solid #1e2d52",
                    border_radius="10px",
                    padding="1rem",
                    font_family="monospace",
                    font_size="13px",
                    resize="vertical",
                ),

                # ── Progress label ──
                rx.cond(
                    State.is_loading,
                    rx.text(State.progress_label, font_size="12px", color="#8899cc"),
                    rx.box(),
                ),

                # ═══════════════════════════════════════
                # RESULTS (shown after analysis)
                # ═══════════════════════════════════════
                rx.cond(
                    State.analysis_done,
                    rx.vstack(
                        rx.divider(border_color="#1e2d52"),

                        # ── Metrics ──
                        rx.grid(
                            rx.box(
                                rx.text("Quality Grade", **LABEL),
                                rx.text(
                                    State.grade,
                                    font_size="36px", font_weight="700",
                                    font_family="monospace",
                                    color="#22c55e",
                                ),
                                **CARD,
                            ),
                            rx.box(
                                rx.text("Issues Found", **LABEL),
                                rx.text(
                                    State.issue_count.to_string(),
                                    font_size="36px", font_weight="700",
                                    font_family="monospace",
                                    color="#f87171",
                                ),
                                **CARD,
                            ),
                            columns="2", gap="12px", width="100%",
                        ),

                        # ── Summary ──
                        _section_card(
                            "📋", "Analysis Summary",
                            rx.text(State.summary, font_size="13px",
                                    color="#8899cc", line_height="1.8"),
                        ),

                        # ── Side by side ──
                        _section_card(
                            "↔", "Side-by-Side Comparison",
                            rx.grid(
                                rx.box(
                                    rx.text("Original", font_size="11px",
                                            font_weight="600", color="#f87171",
                                            text_transform="uppercase",
                                            letter_spacing=".06em",
                                            padding="8px 14px",
                                            border_bottom="1px solid #1e2d52",
                                            background="rgba(248,113,113,.05)"),
                                    rx.box(
                                        rx.text(State.code_input,
                                                font_family="monospace",
                                                font_size="12px",
                                                white_space="pre-wrap",
                                                word_break="break-word"),
                                        padding="14px",
                                        max_height="300px",
                                        overflow_y="auto",
                                    ),
                                    border="1px solid #1e2d52",
                                    border_radius="8px",
                                    overflow="hidden",
                                ),
                                rx.box(
                                    rx.text("Improved", font_size="11px",
                                            font_weight="600", color="#22c55e",
                                            text_transform="uppercase",
                                            letter_spacing=".06em",
                                            padding="8px 14px",
                                            border_bottom="1px solid #1e2d52",
                                            background="rgba(34,197,94,.05)"),
                                    rx.box(
                                        rx.text(State.corrected_code,
                                                font_family="monospace",
                                                font_size="12px",
                                                white_space="pre-wrap",
                                                word_break="break-word"),
                                        padding="14px",
                                        max_height="300px",
                                        overflow_y="auto",
                                    ),
                                    border="1px solid #22c55e44",
                                    border_radius="8px",
                                    overflow="hidden",
                                ),
                                columns="2", gap="12px",
                            ),
                        ),

                        # ── Issues ──
                        _section_card(
                            "⚠", "Issues Found",
                            rx.cond(
                                State.issues.length() == 0,
                                rx.text("✓ No issues detected.", color="#22c55e",
                                        font_size="13px"),
                                rx.vstack(
                                    rx.foreach(State.issues, _issue_row),
                                    width="100%", spacing="0",
                                ),
                            ),
                        ),

                        # ── Improved Code (full) ──
                        _section_card(
                            "✨", "Improved Code",
                            rx.box(
                                rx.text(State.corrected_code,
                                        font_family="monospace",
                                        font_size="12px",
                                        line_height="1.6",
                                        white_space="pre-wrap",
                                        word_break="break-word"),
                                background="#0a0e1a",
                                border="1px solid #1e2d52",
                                border_radius="8px",
                                padding="1rem",
                                max_height="400px",
                                overflow_y="auto",
                            ),
                        ),

                        # ── Static Analysis ──
                        _section_card(
                            "🔍", "Static Analysis",
                            rx.vstack(
                                rx.grid(
                                    rx.box(
                                        rx.text("Unused Imports", **LABEL),
                                        rx.flex(
                                            rx.foreach(
                                                State.unused_imports,
                                                lambda v: _pill(v, "#fbbf24"),
                                            ),
                                            rx.cond(
                                                State.unused_imports.length() == 0,
                                                rx.text("None", font_size="12px",
                                                        color="#4a5a8a",
                                                        font_style="italic"),
                                                rx.box(),
                                            ),
                                            flex_wrap="wrap",
                                        ),
                                        **CARD_DARK,
                                    ),
                                    rx.box(
                                        rx.text("Unused Functions", **LABEL),
                                        rx.flex(
                                            rx.foreach(
                                                State.unused_functions,
                                                lambda v: _pill(v, "#f87171"),
                                            ),
                                            rx.cond(
                                                State.unused_functions.length() == 0,
                                                rx.text("None", font_size="12px",
                                                        color="#4a5a8a",
                                                        font_style="italic"),
                                                rx.box(),
                                            ),
                                            flex_wrap="wrap",
                                        ),
                                        **CARD_DARK,
                                    ),
                                    rx.box(
                                        rx.text("Unused Variables", **LABEL),
                                        rx.flex(
                                            rx.foreach(
                                                State.unused_variables,
                                                lambda v: _pill(v, "#a78bfa"),
                                            ),
                                            rx.cond(
                                                State.unused_variables.length() == 0,
                                                rx.text("None", font_size="12px",
                                                        color="#4a5a8a",
                                                        font_style="italic"),
                                                rx.box(),
                                            ),
                                            flex_wrap="wrap",
                                        ),
                                        **CARD_DARK,
                                    ),
                                    rx.box(
                                        rx.text("Style Violations", **LABEL),
                                        rx.flex(
                                            rx.foreach(
                                                State.style_violations,
                                                lambda v: _pill(v, "#4f8ef7"),
                                            ),
                                            rx.cond(
                                                State.style_violations.length() == 0,
                                                rx.text("None", font_size="12px",
                                                        color="#4a5a8a",
                                                        font_style="italic"),
                                                rx.box(),
                                            ),
                                            flex_wrap="wrap",
                                        ),
                                        **CARD_DARK,
                                    ),
                                    columns="2", gap="12px",
                                ),
                                # Linter status
                                rx.box(
                                    rx.text("External Linter Tool Status", **LABEL),
                                    rx.foreach(
                                        State.linter_tools,
                                        lambda t: rx.flex(
                                            rx.text(t, font_size="13px", color="#e2e8f8"),
                                            rx.flex(
                                                rx.box(width="7px", height="7px",
                                                       border_radius="50%",
                                                       background="#fbbf24"),
                                                rx.text("simulated", font_size="12px",
                                                        color="#fbbf24"),
                                                gap="6px", align="center",
                                            ),
                                            justify="between",
                                            padding="8px 0",
                                            border_bottom="1px solid #1e2d52",
                                        ),
                                    ),
                                    **CARD_DARK,
                                ),
                                width="100%", spacing="3",
                            ),
                        ),

                        # ── Variable Context ──
                        _section_card(
                            "⊕", "Variable Context (code_visitor)",
                            rx.grid(
                                rx.box(
                                    rx.text("Created Variables", **LABEL),
                                    rx.flex(
                                        rx.foreach(
                                            State.created_vars,
                                            lambda v: _pill(v, "#2dd4bf"),
                                        ),
                                        rx.cond(
                                            State.created_vars.length() == 0,
                                            rx.text("None", font_size="12px",
                                                    color="#4a5a8a",
                                                    font_style="italic"),
                                            rx.box(),
                                        ),
                                        flex_wrap="wrap",
                                    ),
                                    **CARD_DARK,
                                ),
                                rx.box(
                                    rx.text("Used Variables", **LABEL),
                                    rx.flex(
                                        rx.foreach(
                                            State.used_vars,
                                            lambda v: _pill(v, "#22c55e"),
                                        ),
                                        rx.cond(
                                            State.used_vars.length() == 0,
                                            rx.text("None", font_size="12px",
                                                    color="#4a5a8a",
                                                    font_style="italic"),
                                            rx.box(),
                                        ),
                                        flex_wrap="wrap",
                                    ),
                                    **CARD_DARK,
                                ),
                                columns="2", gap="12px",
                            ),
                        ),

                        width="100%", spacing="4",
                    ),
                    rx.box(),  # placeholder when not done
                ),

                spacing="5", width="100%",
            ),
            **CONTAINER,
        ),
        **PAGE_BG,
    )


# ══════════════════════════════════════════════════════════════════
#  PAGE: AI ASSISTANT  (/assistant)
# ══════════════════════════════════════════════════════════════════

def _chat_bubble(msg: ChatMessage) -> rx.Component:
    is_user = msg.role == "user"
    return rx.flex(
        rx.box(
            rx.text(
                rx.cond(is_user, "U", "AI"),
                font_size="11px", font_weight="600", color="white",
            ),
            background=rx.cond(is_user, "#4f8ef7", "linear-gradient(135deg,#2563eb,#7c3aed)"),
            width="30px", height="30px",
            border_radius="50%",
            display="flex", align_items="center", justify_content="center",
            flex_shrink="0",
        ),
        rx.box(
            rx.text(msg.content, font_size="13px", line_height="1.7",
                    white_space="pre-wrap", word_break="break-word"),
            background=rx.cond(is_user, "#4f8ef7", "#141c35"),
            color=rx.cond(is_user, "white", "#e2e8f8"),
            border=rx.cond(is_user, "none", "1px solid #1e2d52"),
            border_radius="10px",
            padding="10px 14px",
            max_width="80%",
        ),
        flex_direction=rx.cond(is_user, "row-reverse", "row"),
        gap="10px",
        align="flex-start",
    )


def assistant() -> rx.Component:
    return rx.box(
        navbar(),
        rx.container(
            rx.vstack(
                rx.flex(
                    rx.vstack(
                        rx.heading("AI Assistant", **H1),
                        spacing="0",
                    ),
                    rx.button(
                        "Clear Chat",
                        on_click=State.clear_chat,
                        background="rgba(248,113,113,.1)",
                        color="#f87171",
                        border="1px solid rgba(248,113,113,.2)",
                        border_radius="6px",
                        font_size="12px",
                        padding="7px 14px",
                        cursor="pointer",
                    ),
                    justify="between", align="center", width="100%",
                    margin_bottom="1.25rem",
                ),

                # Chat window
                rx.box(
                    rx.cond(
                        State.chat_messages.length() == 0,
                        rx.vstack(
                            rx.text("💬", font_size="36px", opacity=".4"),
                            rx.text("Ask the AI Assistant", font_size="14px",
                                    font_weight="500"),
                            rx.text(
                                "Ask follow-up questions on your analysis,"
                                " suggested fixes, security, or optimizations.",
                                font_size="12px", color="#4a5a8a",
                                text_align="center", max_width="360px",
                            ),
                            rx.text(
                                "No messages yet. Ask your first question about the analyzed code.",
                                font_size="11px", color="#4a5a8a",
                            ),
                            align="center", justify="center",
                            height="100%", width="100%",
                        ),
                        rx.vstack(
                            rx.foreach(State.chat_messages, _chat_bubble),
                            width="100%", spacing="3",
                        ),
                    ),
                    background="#0f1628",
                    border="1px solid #1e2d52",
                    border_radius="10px 10px 0 0",
                    padding="1rem",
                    height="420px",
                    overflow_y="auto",
                    width="100%",
                ),

                # Input row
                rx.flex(
                    rx.text_area(
                        placeholder="Ask about the analyzed code...",
                        value=State.chat_input,
                        on_change=State.set_chat_input,
                        background="#0f1628",
                        color="#e2e8f8",
                        border="1px solid #243460",
                        border_radius="8px",
                        padding="10px 14px",
                        font_size="13px",
                        flex="1",
                        height="44px",
                        resize="none",
                    ),
                    rx.button(
                        rx.cond(State.is_chatting, "...", "Send"),
                        on_click=State.send_chat,
                        loading=State.is_chatting,
                        background="#4f8ef7",
                        color="white",
                        border_radius="8px",
                        padding="0 18px",
                        height="44px",
                        font_size="14px",
                        cursor="pointer",
                        _hover={"background": "#3a6fd4"},
                    ),
                    gap="8px",
                    padding="12px",
                    background="#141c35",
                    border="1px solid #1e2d52",
                    border_top="none",
                    border_radius="0 0 10px 10px",
                    width="100%",
                ),
                rx.text(
                    "Connected to your latest analysis context.",
                    font_size="11px", color="#4a5a8a", text_align="center",
                ),
                width="100%", spacing="0",
            ),
            **CONTAINER,
        ),
        **PAGE_BG,
    )


# ══════════════════════════════════════════════════════════════════
#  PAGE: HISTORY  (/history)
# ══════════════════════════════════════════════════════════════════

def _history_card(item: HistoryItem, idx: int) -> rx.Component:
    lang_colors = {
        "python": "#22c55e", "javascript": "#fbbf24",
        "typescript": "#4f8ef7", "java": "#f87171",
        "go": "#2dd4bf", "rust": "#a78bfa", "c": "#8899cc", "cpp": "#a78bfa",
    }
    return rx.box(
        # Header row
        rx.flex(
            rx.text(
                item.language,
                font_size="11px", padding="2px 10px",
                border_radius="20px", font_weight="500",
                background="rgba(34,197,94,.1)",
                color="#22c55e",
                border="1px solid rgba(34,197,94,.2)",
            ),
            rx.text(
                item.original_code[:60] + "...",
                font_size="12px", font_family="monospace",
                color="#8899cc", flex="1",
                overflow="hidden", white_space="nowrap", text_overflow="ellipsis",
            ),
            rx.text(item.grade, font_size="14px", font_weight="700",
                    font_family="monospace", color="#22c55e"),
            rx.text(item.ts, font_size="11px", color="#4a5a8a"),
            rx.text("▾", font_size="12px", color="#4a5a8a"),
            gap="12px", align="center",
            padding="14px 18px",
            cursor="pointer",
            on_click=lambda: State.toggle_history_item(idx),
            _hover={"background": "#141c35"},
            border_radius=rx.cond(item.expanded, "10px 10px 0 0", "10px"),
        ),
        # Expandable body
        rx.cond(
            item.expanded,
            rx.box(
                rx.text(item.summary, font_size="13px",
                        color="#8899cc", line_height="1.7",
                        margin_bottom="10px"),
                rx.text("Original Code", font_size="11px",
                        color="#4a5a8a", margin_bottom="6px"),
                rx.box(
                    rx.text(item.original_code,
                            font_family="monospace", font_size="11px",
                            white_space="pre-wrap", word_break="break-word"),
                    background="#0a0e1a",
                    border="1px solid #1e2d52",
                    border_radius="6px",
                    padding="12px",
                    max_height="200px",
                    overflow_y="auto",
                    margin_bottom="10px",
                ),
                rx.text("Improved Code", font_size="11px",
                        color="#22c55e", margin_bottom="6px"),
                rx.box(
                    rx.text(item.corrected_code,
                            font_family="monospace", font_size="11px",
                            white_space="pre-wrap", word_break="break-word"),
                    background="#0a0e1a",
                    border="1px solid #22c55e33",
                    border_radius="6px",
                    padding="12px",
                    max_height="200px",
                    overflow_y="auto",
                ),
                padding="14px 18px",
                border_top="1px solid #1e2d52",
            ),
            rx.box(),
        ),
        background="#0f1628",
        border="1px solid #1e2d52",
        border_radius="10px",
        overflow="hidden",
        margin_bottom="12px",
    )


def history() -> rx.Component:
    return rx.box(
        navbar(),
        rx.container(
            rx.vstack(
                rx.flex(
                    rx.heading("Review History", **H1),
                    rx.button(
                        "Clear History",
                        on_click=State.clear_history,
                        background="rgba(248,113,113,.1)",
                        color="#f87171",
                        border="1px solid rgba(248,113,113,.2)",
                        border_radius="6px",
                        font_size="12px",
                        padding="7px 14px",
                        cursor="pointer",
                    ),
                    justify="between", align="center", width="100%",
                    margin_bottom="1.5rem",
                ),
                rx.cond(
                    State.history.length() == 0,
                    rx.vstack(
                        rx.text("🕐", font_size="40px", opacity=".4"),
                        rx.text("No reviews yet. Analyze code from the Review Code page.",
                                font_size="13px", color="#4a5a8a"),
                        align="center", padding="3rem",
                    ),
                    rx.vstack(
                        rx.foreach(
                            State.history,
                            lambda item, idx: _history_card(item, idx),
                        ),
                        width="100%", spacing="0",
                    ),
                ),
                width="100%", spacing="0",
            ),
            **CONTAINER,
        ),
        **PAGE_BG,
    )


# ══════════════════════════════════════════════════════════════════
#  PAGE: ABOUT  (/about)
# ══════════════════════════════════════════════════════════════════

def about() -> rx.Component:
    features = [
        ("🌐", "Multi-Language Parsing",
         "Parses Python, JS/TS, Java, C/C++, Go, Rust and checks syntax health."),
        ("🔍", "Static Analysis",
         "Detects unused imports, functions, variables with language-aware rules."),
        ("⚙️", "External Linting",
         "Shows expected tools: ESLint/tsc, go vet, rustc, javac, gcc."),
        ("🤖", "AI Suggestions",
         "Uses Groq LLaMA 3.1 to summarize quality issues and generate improved code."),
        ("↔️", "Side-by-Side View",
         "Compares original vs improved code clearly."),
        ("📋", "Review History",
         "Stores interactive review history with expandable full details."),
    ]

    pipeline = [
        ("User submits code from Review Code page.", "1"),
        ("code_parser validates syntax and catches parse errors.", "2"),
        ("error_detector detects unused symbols and variable context.", "3"),
        ("ai_suggester generates a quality summary and improved code.", "4"),
        ("Results are rendered as metrics, issues, and comparisons.", "5"),
    ]

    return rx.box(
        navbar(),
        rx.container(
            rx.vstack(
                rx.heading("About AI Code Reviewer", **H1),
                rx.text(
                    "AI Code Reviewer is a Reflex-powered platform for automated code quality analysis. "
                    "It combines language-aware static analysis with AI-generated suggestions so students "
                    "and instructors can review code faster with clear, actionable feedback.",
                    color="#8899cc", font_size="14px", line_height="1.8",
                    margin_bottom="2rem",
                ),

                rx.heading("What This App Does", size="5",
                           font_weight="600", margin_bottom="1rem"),
                rx.grid(
                    *[
                        rx.box(
                            rx.flex(
                                rx.text(icon, font_size="18px"),
                                rx.vstack(
                                    rx.text(title, font_size="13px",
                                            font_weight="500", margin_bottom="3px"),
                                    rx.text(desc, font_size="12px",
                                            color="#8899cc", line_height="1.6"),
                                    spacing="1",
                                ),
                                gap="10px", align="flex-start",
                            ),
                            **CARD,
                        )
                        for icon, title, desc in features
                    ],
                    columns="2", gap="10px", width="100%",
                    margin_bottom="2rem",
                ),

                rx.heading("Analysis Pipeline", size="5",
                           font_weight="600", margin_bottom="1rem"),
                rx.vstack(
                    *[
                        rx.flex(
                            rx.box(
                                rx.text(num, font_size="11px",
                                        font_weight="700", color="white"),
                                background="#4f8ef7",
                                width="24px", height="24px",
                                border_radius="50%",
                                display="flex",
                                align_items="center",
                                justify_content="center",
                                flex_shrink="0",
                            ),
                            rx.text(step, font_size="13px", color="#8899cc"),
                            gap="12px", align="center",
                            **CARD,
                        )
                        for step, num in pipeline
                    ],
                    width="100%", spacing="2", margin_bottom="2rem",
                ),

                rx.heading("Technology Stack", size="5",
                           font_weight="600", margin_bottom="1rem"),
                rx.grid(
                    rx.box(rx.text("Frontend", font_size="12px",
                                   font_weight="500", margin_bottom="3px"),
                           rx.text("Reflex (Python)", font_size="11px",
                                   color="#4a5a8a"),
                           **CARD, text_align="center"),
                    rx.box(rx.text("Backend Logic", font_size="12px",
                                   font_weight="500", margin_bottom="3px"),
                           rx.text("code_parser\nerror_detector\nai_suggester\nanalyzer",
                                   font_size="11px", color="#4a5a8a",
                                   white_space="pre"),
                           **CARD, text_align="center"),
                    rx.box(rx.text("AI Integration", font_size="12px",
                                   font_weight="500", margin_bottom="3px"),
                           rx.text("Groq LLaMA 3.1\nvia LangChain",
                                   font_size="11px", color="#4a5a8a",
                                   white_space="pre"),
                           **CARD, text_align="center"),
                    rx.box(rx.text("Outputs", font_size="12px",
                                   font_weight="500", margin_bottom="3px"),
                           rx.text("Grade · Issues\nImproved Code\nPDF Report",
                                   font_size="11px", color="#4a5a8a",
                                   white_space="pre"),
                           **CARD, text_align="center"),
                    columns="4", gap="10px", width="100%",
                ),

                width="100%", spacing="3",
            ),
            **CONTAINER,
        ),
        **PAGE_BG,
    )


# ══════════════════════════════════════════════════════════════════
#  APP SETUP
# ══════════════════════════════════════════════════════════════════

app = rx.App(
    theme=rx.theme(appearance="dark"),
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Sora:wght@300;400;500;600;700&display=swap"
    ],
)

# Register all pages (following the class notes pattern)
app.add_page(index, route="/")
app.add_page(posts, route="/posts")
app.add_page(assistant, route="/assistant")
app.add_page(history, route="/history")
app.add_page(about, route="/about")
