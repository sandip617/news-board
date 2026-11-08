# Set up News Board with Claude

Open this folder in Claude Code, then paste these prompts one at a time.

## Step 1: Publish the board

Paste this:

```
Publish index.html in this folder as a new claude.ai Artifact.
- Also publish these files next to it: data/index.json, data/terms.json and every file in data/days/, at the same paths.
- Use the icon "newspaper".
- Declare these capabilities exactly:
  {"db": {"rules": [
     {"path": "", "read": "view", "write": "owner"},
     {"path": "data/users/{self}", "write": "interact"},
     {"path": "suggestions", "read": "view", "write": "owner"},
     {"path": "suggestions/{self}", "read": "view", "write": "interact"}
  ]}, "user": {}, "sample": {}}
When it's done, give me the artifact link.
```

What the capabilities do: everyone who opens the board can read it, only you can change the news, each reader can save their own notes, quiz results and flashcard progress and suggest one blog topic, and readers can use "Ask AI" under a story (`sample`; each reader is asked once and it uses their own Claude plan).

Copy the link Claude gives you (it looks like `https://claude.ai/artifact/...`).

## Step 2: Create the daily update

First open `ROUTINE_PROMPT.md` and replace `YOUR_ARTIFACT_URL` with your link, and `SENDER_EMAIL` with your verified sender address (see "Email subscription setup" in the README; leave it as is for now if you don't want emails yet, and the routine will skip the email). If you forked the repo, also change `sandip617/news-board` and the `sandip617.github.io` links to your own. Save the file. Then paste this:

```
/schedule Create a routine named "News Board – daily edition".
- Run every day at 6:45 AM India time (cron "15 1 * * *" in UTC).
- Model: claude-sonnet-5-5.
- Git repository: sandip617/news-board, with push access to main.
- Connectors: MailerLite.
- Allowed tools: Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch, Artifact, ArtifactData, and the MailerLite tools search, list_campaigns, list_resources, create_campaign, validate_subject_lines, validate_email_content, schedule_campaign.
- The prompt is the full text of ROUTINE_PROMPT.md in this folder, word for word.
Show me the routine link when it's created.
```

If you live outside India, change the time. Cron times are in UTC: 7 AM in London (winter) is `0 7 * * *`, 7 AM in New York (winter) is `0 12 * * *`.

## Step 3: Test it

```
Run the News Board routine now, wait for it to finish, then tell me whether it published a new edition, pushed to GitHub and sent the email.
```

## Already have a board? Update it

If you set up your board before the glossary, Ask AI and email features, paste these two prompts in order.

**1. Update the board page and its capabilities**

```
Update my existing News Board artifact (find it in my artifacts, or use YOUR_ARTIFACT_URL).
- Read it first. Then republish index.html from this folder to the same URL, together with data/index.json, data/terms.json and every file in data/days/, at the same paths.
- Declare these capabilities exactly (this adds "sample" for Ask AI and keeps everything else):
  {"db": {"rules": [
     {"path": "", "read": "view", "write": "owner"},
     {"path": "data/users/{self}", "write": "interact"},
     {"path": "suggestions", "read": "view", "write": "owner"},
     {"path": "suggestions/{self}", "read": "view", "write": "interact"}
  ]}, "user": {}, "sample": {}}
- Don't change anything else. Tell me when it's live.
```

**2. Update the daily routine**

```
Update my existing "News Board" routine (find it in my routines):
- Replace its prompt with the full text of ROUTINE_PROMPT.md in this folder, word for word.
- Attach the Git repository sandip617/news-board with push access to main.
- Attach the MailerLite connector, and add the MailerLite tools search, list_campaigns, list_resources, create_campaign, validate_subject_lines, validate_email_content, schedule_campaign to the allowed tools.
- Keep the schedule and model as they are.
Show me the routine link and the next run time.
```

## Changing things later

- **Rewrite today's blog:** "Rewrite today's blog on the News Board in simpler Bangla" (or name a new topic).
- **Change the design:** edit `index.html`, then "Republish index.html to my News Board artifact."
- **Change what the routine writes:** edit `ROUTINE_PROMPT.md`, then "Update the News Board routine with the new ROUTINE_PROMPT.md."
- **Pause it:** https://claude.ai/code/routines
