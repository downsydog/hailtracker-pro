# RULES - READ THIS FIRST EVERY TIME

1. Read TODO.md and STATE.md FIRST before doing anything
2. Do ONLY the next incomplete task - the first task with [ ] not [x]
3. Do NOT move to the next task until current task is VERIFIED
4. LOOP on errors - try at least 3 different approaches before marking blocked
5. After completing a task, update STATE.md with what you did and proof it works
6. Mark the task [x] in TODO.md when verified complete
7. Git commit after each completed task with descriptive message

CRITICAL RULES - VIOLATING THESE WILL BREAK THE APP:
8. ALL BACKEND WORK HAPPENS IN src/. NEVER create new files in backend/.
9. DO NOT delete, replace, or overwrite any existing file in src/.
10. DO NOT create a new backend folder or reorganize the file structure.
11. ADD code to existing files or create NEW files inside src/.
12. The backend/ folder is REFERENCE ONLY. You may READ it for ideas but NEVER import from it.
13. The app MUST still work after every change. Test by hitting http://localhost:5000/api/health
14. If the app breaks, revert your changes immediately with git checkout.
15. The frontend is in frontend/. The backend is in src/. The server is scripts/test_api_server.py.
16. DO NOT change which backend the frontend connects to. It connects to src/ on port 5000.
17. NEVER use mock data. NEVER use placeholder code. Every feature must actually work.
18. Keep API kill switch ACTIVE (API_CALLS_ENABLED=false). Do not re-enable APIs.
