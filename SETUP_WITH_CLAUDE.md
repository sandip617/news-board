# Set up News Board with Claude

Open this folder in Claude Code, then paste these prompts one at a time.

## Step 1: Publish the board

Paste this:

```
Publish index.html in this folder as a new claude.ai Artifact.
- Also publish these files next to it: data/index.json and every file in data/days/, at the same paths.
- Use the icon "newspaper".
- Declare these capabilities exactly:
  {"db": {"rules": [
     {"path": "", "read": "view", "write": "owner"},
     {"path": "data/users/{self}", "write": "interact"},
     {"path": "suggestions", "read": "view", "write": "owner"},
     {"path": "suggestions/{self}", "read": "view", "write": "interact"}
  ]}, "user": {}}
When it's done, give me the artifact link.
```

What the capabilities do: everyone who opens the board can read it, only you can change the news, and each reader can save their own notes and suggest one blog topic.

Copy the link Claude gives you (it looks like `https://claude.ai/artifact/...`).

## Step 2: Create the daily update

First open `ROUTINE_PROMPT.md` and replace `YOUR_ARTIFACT_URL` with your link. Save the file. Then paste this:

```
/schedule Create a routine named "News Board – daily edition".
- Run every day at 6:45 AM India time (cron "15 1 * * *" in UTC).
- Model: claude-sonnet-5-5. No git repository. No connectors.
- Allowed tools: Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch, Artifact, ArtifactData.
- The prompt is the full text of ROUTINE_PROMPT.md in this folder, word for word.
Show me the routine link when it's created.
```

If you live outside India, change the time. Cron times are in UTC: 7 AM in London (winter) is `0 7 * * *`, 7 AM in New York (winter) is `0 12 * * *`.

## Step 3: Test it

```
Run the News Board routine now, wait for it to finish, then tell me whether it published a new edition.
```

## Changing things later

- **Rewrite today's blog:** "Rewrite today's blog on the News Board in simpler Bangla" (or name a new topic).
- **Change the design:** edit `index.html`, then "Republish index.html to my News Board artifact."
- **Change what the routine writes:** edit `ROUTINE_PROMPT.md`, then "Update the News Board routine with the new ROUTINE_PROMPT.md."
- **Pause it:** https://claude.ai/code/routines
