from __future__ import annotations


def answer_question(question: str, weekly_rows: list[dict[str, object]], blocks: list[dict[str, object]]) -> str:
    lowered = question.lower()
    if "where did my time go" in lowered:
        parts = [f"{row['category']}: {row['total_minutes']}m" for row in weekly_rows[:5]]
        return "Last week was mostly split across " + ", ".join(parts) + "."
    if "largest unknown gaps" in lowered:
        return "Use the weekly report gaps section; unknown time has been preserved explicitly."
    if "deep work" in lowered:
        deep = next((row for row in weekly_rows if row["category"] == "deep_work"), None)
        return f"Deep work totaled {deep['total_minutes']} minutes." if deep else "No deep-work evidence found."
    return "I can answer scoped time-use questions from the derived mart after build/report runs."
