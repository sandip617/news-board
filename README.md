# News Board

A daily business newspaper for BBA students, in **Bangla and English**. Every morning it gets a new edition with the day's most important global business news, an AI-written blog, a business term, a GD topic, a 5-question quiz, a weekly case study and a market snapshot.

**Live:** https://news.itzsandippal.com/ (a new edition every morning)
**Made by:** [Sandip Pal](https://itzsandippal.com)

## What's on the board

| Section | What it does |
|---|---|
| Today's news | 7–8 global business stories, each with a short summary, "why a BBA student should care" and a link to the source |
| Market snapshot | S&P 500, Dow, Nasdaq, Sensex, Nifty 50, Brent crude, gold, USD/INR |
| Blog | A 600–900 word explainer on one business idea, tied to the day's news |
| Term of the day | One business term with a definition, example, formula and interview tip |
| GD topic | A group-discussion topic with 3 points for and 3 against |
| Quiz | 5 MCQs from the day's news, with instant answers and explanations |
| Case study of the week | A real company strategy (new every Monday) |
| Share | Share any story or the whole edition (WhatsApp, copy link, or your phone's share menu). Links like `#2026-11-05/n3` open that exact story |
| Ask AI | Under each story: ask Claude to explain it more simply, its impact, or your own question (only on claude.ai) |
| Quiz streak | Your daily streak, best streak and total correct answers, with the last 14 days as dots |
| Weekly revision | On Sundays: the week's 5 key points and a 10-question quiz |
| Glossary | Every Term of the Day as flip cards, with search, shuffle and "I know it / Review again" |
| My notebook | Save stories and write notes (private to each reader); see all notes in one list and download them as a .txt file |
| Archive | Every past edition, grouped by month, with search |
| Email | Readers can subscribe and get a short digest every morning (MailerLite, double opt-in) |
| Bangla / English | One button switches the whole board |
| Light / dark mode | Follows your device, or pick one |

## Two ways to run your own

### Option A: Free, on GitHub Pages (you update it yourself)

Good if you just want the board online. It won't update by itself.

1. Click **Fork** at the top of this page (you need a free GitHub account).
2. In your fork, go to **Settings → Pages**. Under "Branch", pick `main` and `/ (root)`, then **Save**.
3. Wait a minute. Your board is live at `https://YOUR-USERNAME.github.io/news-board/`.
4. To post a new edition, add a file in `data/days/` named like `2026-11-04.json` (copy an existing one and change the content), then add it to the top of `data/index.json`, set `"latest"` to the new date, and run `python3 scripts/build_terms.py` to refresh the glossary.

On GitHub Pages the "suggest a blog topic" box and "Ask AI" are hidden, and notes, quiz results and flashcard progress are saved in each reader's browser.

### Option B: Automatic every morning, with Claude

The board updates by itself at 7 AM. You need a paid Claude plan (Pro or Max) with [Claude Code](https://claude.com/claude-code).

1. **Get the code.** Download this repo (green **Code** button → **Download ZIP**) and unzip it. Or run `git clone https://github.com/sandip617/news-board`.
2. **Open it in Claude Code.** Open the `news-board` folder in Claude Code (terminal, VS Code or the desktop app).
3. **Publish the board.** Paste the prompt from [SETUP_WITH_CLAUDE.md](SETUP_WITH_CLAUDE.md) (step 1). Claude publishes the board on claude.ai and gives you a link like `https://claude.ai/artifact/...`. Copy it.
4. **Set up the daily update.** Open [ROUTINE_PROMPT.md](ROUTINE_PROMPT.md) and replace `YOUR_ARTIFACT_URL` with your link. Then paste the prompt from SETUP_WITH_CLAUDE.md (step 2). Claude creates a daily "routine" that runs at 6:45 AM India time and publishes a new edition by 7 AM.
5. **Test it.** Ask Claude: "Run the News Board routine now." After about 5 minutes, open your link and check the new edition.
6. **Share it.** On your board, open the **Share** menu and choose who can see it. To let people suggest blog topics, give them **Contributor** access.

You can see, pause or delete the daily update at https://claude.ai/code/routines.

## Email subscription setup

The board can email a short digest every morning. You need a free [MailerLite](https://www.mailerlite.com) account.

1. **Create a group.** In MailerLite go to **Subscribers → Groups** and create a group named exactly `News Board subscribers`.
2. **Create a form.** Go to **Forms → Embedded forms → Create form**, pick the `News Board subscribers` group, and turn on **double opt-in** (MailerLite then sends each new subscriber a confirmation mail). Publish the form.
3. **Copy the form's action URL.** In the form's **HTML code**, find `<form ... action="https://assets.mailerlite.com/jsonp/.../subscribe"`. Copy that URL and paste it into `index.html` as `CONFIG.SUBSCRIBE_ACTION` (at the top of the script). Until you do, the Subscribe section stays hidden.
4. **Verify a sender.** Go to **Settings → Domains**, add your own domain (e.g. `itzsandippal.com`) and follow the DNS steps. Then put a sender address on that domain (e.g. `news@itzsandippal.com`) into `ROUTINE_PROMPT.md` in place of `SENDER_EMAIL`.
5. **Connect MailerLite to Claude.** On claude.ai, open **Settings → Connectors** and connect MailerLite. Then update the routine (see "Already have a board? Update it" in [SETUP_WITH_CLAUDE.md](SETUP_WITH_CLAUDE.md)).
6. Push `index.html` to GitHub and republish it to your artifact.

Inside claude.ai the form doesn't post; it shows a button that opens the public page's Subscribe section instead. The routine sends at most one email a day, never on a re-run, and skips the email while `SENDER_EMAIL` is still a placeholder.

## Make it yours

| Change | Where |
|---|---|
| Public link, email form | `index.html`: `CONFIG` at the top of the script (`PUBLIC_URL`, `SUBSCRIBE_ACTION`) |
| Board name ("Sandip's Board") | `index.html`: the `<title>`, the `<h1>` in the masthead, and the two `footer:` lines in the script |
| Tagline and menu text | `index.html`: the `T` object near the top of the script (`bn` = Bangla, `en` = English) |
| Colours | `index.html`: the `--paper`, `--ink`, `--red` values in `:root` (light) and the two dark-mode blocks |
| Fonts | `index.html`: the Google Fonts link and `--f-mast`, `--f-body`, `--f-ui` |
| Who the news is for (e.g. MBA, engineering, school students) | `ROUTINE_PROMPT.md`: change "BBA students" and the topics in Step 4 |
| Update time | Ask Claude: "Change the News Board routine to run at 6 AM India time." |
| Languages | `ROUTINE_PROMPT.md` Step 5, and the `T` object in `index.html` |

After you change `index.html`, ask Claude to republish it to your artifact link. After you change `ROUTINE_PROMPT.md`, ask Claude to update the routine with the new prompt.

## Files

```
index.html               the board (one page, no build step)
data/index.json          list of editions, newest first
data/days/YYYY-MM-DD.json one edition: Bangla content at the top, English under "en"
                         (optional "weekly" on Sundays)
data/terms.json          every Term of the Day, newest first (for the glossary)
scripts/build_terms.py   rebuilds data/terms.json from data/days/ (one-off helper)
ROUTINE_PROMPT.md        the instructions the daily Claude routine follows
SETUP_WITH_CLAUDE.md     prompts to publish the board and create the routine
```

## Notes

- News comes from web search, and every story links to its source. Numbers can sometimes be slightly off, so check the source before you quote it.
- Nothing here is investment advice.

## License

MIT. Use it, change it, share it.
