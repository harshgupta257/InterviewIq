# Demonstration script (≈5 minutes)

**Setup.** Start the backend and frontend as in the README quick start. For the strongest demo,
set `AI_PROVIDER=gemini` with a key. The demo login still works, and questions and feedback
become real AI output.

1. **Landing (`/`)**: point out the value proposition and the example evaluation card, which is labelled "Example".
2. **Protected routes**: open `/dashboard` while logged out. It redirects to `/login?next=/dashboard`.
3. **Login**: click **Explore the demo**. You get an isolated account seeded with three fictional sessions, badged *Demo*.
4. **Dashboard**:
   - The stats come from the database. Mention the "includes demo data" disclosure.
   - Point out the trend chart (toggle **Show as table**), the rubric averages and the recent sessions.
5. **New interview**:
   - Click **Generate** with empty fields to show the validation messages.
   - Click **Load sample data**, then **Generate my interview**, and watch the staged progress.
   - Mention that cancel works and that nothing is saved if generation fails.
6. **Workspace**:
   - Q1 shows its category, "Why this question?" and the source context.
   - Type an answer and point out the character count and "Draft saved on this device".
   - Submit to see the evaluation: four scores with reasons, the backend-computed percentage, and the one thing to fix.
7. **Stronger answer**: click **Show a stronger answer** to see your answer, the example and "What changed". Point out the placeholders and the "illustrative, not verified" notice.
8. **Resilience**:
   - Refresh the page. It resumes at question 2 and question 1 stays answered.
   - Type a draft and refresh again. The draft is restored.
9. **History**:
   - Search for "fabrikam", filter by role and sort by score.
   - Open a session, use **Expand all**, and show the comparison view and the resume (hidden by default).
   - Click **Practice again**, which prefills the form.
10. **Delete**: delete a session from History through the confirmation dialog.
11. **Settings**: switch to dark mode, show the AI provider disclosure and the account deletion flow (type DELETE).
12. **Security talking points**:
    - Opening another user's session URL shows "not found".
    - Show the `/docs` API.
    - Mention the IDOR, prompt-injection and RLS tests in CI.
