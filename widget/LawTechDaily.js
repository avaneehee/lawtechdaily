// LawTechDaily.js  —  Scriptable widget

// ---------------------------------------------------------------

// Setup:

//   1. Install Scriptable (free, App Store)

//   2. Paste this into a new script named "LawTechDaily"

//   3. Set GITHUB_USER / REPO below

//   4. Long-press home screen -> + -> Scriptable -> Medium size

//      -> Edit Widget -> Script: LawTechDaily, When Interacting: Run Script

// ---------------------------------------------------------------

 

const GITHUB_USER = "YOUR_USERNAME";   // <-- change

const REPO        = "lawtech-daily";

const BRANCH      = "main";

 

const DATA_URL =

  `https://raw.githubusercontent.com/${GITHUB_USER}/${REPO}/${BRANCH}/data/today.json`;

 

// --- palette (your peachy-pink dark theme) -----------------------

const BG_TOP    = new Color("#1c1620");

const BG_BOTTOM = new Color("#120e16");

const ACCENT    = new Color("#ff9090");

const CHIP_BG   = new Color("#ff9090", 0.22);

const TEXT      = new Color("#fff5f3");

const MUTED     = new Color("#c99aa0");

 

// --- fetch with cache fallback ------------------------------------

// Cache means the widget still renders if you're offline or the

// Action hasn't run yet. A widget that shows an error is a dead widget.

const fm = FileManager.local();

const cachePath = fm.joinPath(fm.cacheDirectory(), "lawtech-today.json");

 

async function getData() {

  try {

    const data = await new Request(DATA_URL).loadJSON();

    fm.writeString(cachePath, JSON.stringify(data));

    return data;

  } catch (e) {

    if (fm.fileExists(cachePath)) return JSON.parse(fm.readString(cachePath));

    return {

      title: "No article yet",

      summary: "Run the GitHub Action, or check your username in the script.",

      tag: "SETUP",

      link: `https://github.com/${GITHUB_USER}/${REPO}`,

      date: "",

    };

  }

}

 

const d = await getData();

const w = new ListWidget();

 

const g = new LinearGradient();

g.colors = [BG_TOP, BG_BOTTOM];

g.locations = [0, 1];

w.backgroundGradient = g;

w.setPadding(14, 15, 14, 15);

w.url = d.link;

 

// --- header row: tag chip (left) + date (right) ---

const header = w.addStack();

header.centerAlignContent();

 

const chip = header.addStack();

chip.setPadding(3, 7, 3, 7);

chip.backgroundColor = CHIP_BG;

chip.cornerRadius = 4;

const tagText = chip.addText(d.tag || "LAW TECH");

tagText.font = Font.boldSystemFont(9);

tagText.textColor = ACCENT;

 

header.addSpacer();

 

const date = header.addText(d.date || "");

date.font = Font.mediumSystemFont(10);

date.textColor = MUTED;

 

w.addSpacer(10);

 

// --- title ---

const title = w.addText(d.title);

title.font = Font.boldSystemFont(17);

title.textColor = TEXT;

title.lineLimit = 3;

title.minimumScaleFactor = 0.9;

 

w.addSpacer(8);

 

// --- summary ---

const summary = w.addText(d.summary || "");

summary.font = Font.systemFont(13);

summary.textColor = MUTED;

summary.lineLimit = 4;

summary.minimumScaleFactor = 0.9;

 

w.addSpacer();

 

// refresh tomorrow morning - iOS treats this as a hint, not a guarantee

const tomorrow = new Date();

tomorrow.setDate(tomorrow.getDate() + 1);

tomorrow.setHours(8, 30, 0, 0);

w.refreshAfterDate = tomorrow;

 

if (!config.runsInWidget) await w.presentMedium();

Script.setWidget(w);

Script.complete();
